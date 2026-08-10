import asyncio
import json
import uuid

from fastapi import status
from pywebpush import WebPushException, webpush
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.config import get_settings
from home_manager.core.errors import AppError
from home_manager.notifications.models import PushSubscription
from home_manager.notifications.schemas import PushSubscriptionCreate


class NotificationsDisabledError(AppError):
    code = "NOTIFICATIONS_DISABLED"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    message = "Push notifications are not configured on this server"


class SubscriptionNotFoundError(AppError):
    code = "SUBSCRIPTION_NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Push subscription not found"


def get_vapid_public_key() -> str:
    settings = get_settings()
    if not settings.vapid_public_key:
        raise NotificationsDisabledError()
    return settings.vapid_public_key


async def subscribe(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    user_agent: str | None,
    payload: PushSubscriptionCreate,
) -> PushSubscription:
    existing = await session.scalar(
        select(PushSubscription).where(PushSubscription.endpoint == payload.endpoint)
    )
    if existing is not None:
        existing.tenant_id = tenant_id
        existing.user_id = user_id
        existing.p256dh = payload.keys.p256dh
        existing.auth = payload.keys.auth
        existing.user_agent = user_agent
        await session.flush()
        return existing

    subscription = PushSubscription(
        tenant_id=tenant_id,
        user_id=user_id,
        endpoint=payload.endpoint,
        p256dh=payload.keys.p256dh,
        auth=payload.keys.auth,
        user_agent=user_agent,
    )
    session.add(subscription)
    await session.flush()
    return subscription


async def unsubscribe(
    session: AsyncSession, *, tenant_id: uuid.UUID, user_id: uuid.UUID, endpoint: str
) -> None:
    subscription = await session.scalar(
        select(PushSubscription).where(
            PushSubscription.endpoint == endpoint,
            PushSubscription.tenant_id == tenant_id,
            PushSubscription.user_id == user_id,
        )
    )
    if subscription is None:
        raise SubscriptionNotFoundError()
    await session.delete(subscription)
    await session.flush()


async def send_push(
    session: AsyncSession, *, tenant_id: uuid.UUID, user_id: uuid.UUID, title: str, body: str
) -> int:
    """Best-effort push to every device the target user is subscribed on.

    Returns the number of subscriptions successfully delivered to (0 when
    push isn't configured at all). Never raises: a dead subscription
    (404/410 from the push service) is pruned, anything else is swallowed,
    since a notification failing is never a reason to fail the caller's own
    request. Commits its own pruning/writes, since it's a side channel the
    caller doesn't otherwise manage a transaction for.
    """
    settings = get_settings()
    if not settings.vapid_public_key or not settings.vapid_private_key:
        return 0

    subscriptions = list(
        (
            await session.scalars(
                select(PushSubscription).where(
                    PushSubscription.tenant_id == tenant_id,
                    PushSubscription.user_id == user_id,
                )
            )
        ).all()
    )

    payload = json.dumps({"title": title, "body": body})
    sent = 0
    for subscription in subscriptions:
        subscription_info = {
            "endpoint": subscription.endpoint,
            "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
        }
        try:
            await asyncio.to_thread(
                webpush,
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": settings.vapid_subject},
            )
            sent += 1
        except WebPushException as exc:
            if exc.response is not None and exc.response.status_code in (404, 410):
                await session.delete(subscription)
        except Exception:
            # See docstring: a delivery failure must never fail the caller's request.
            continue

    await session.commit()
    return sent
