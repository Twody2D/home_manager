import uuid
from typing import Any

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.auth.models import User
from home_manager.core.errors import AppError
from home_manager.finance.models import Income, Subscription, SubscriptionCadence
from home_manager.finance.schemas import (
    IncomeCreate,
    IncomeUpdate,
    SubscriptionCreate,
    SubscriptionUpdate,
)


class IncomeNotFoundError(AppError):
    code = "INCOME_NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Income not found"


class InvalidIncomeOwnerError(AppError):
    code = "INVALID_INCOME_OWNER"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    message = "user_id must be a member of the same household"


class SubscriptionNotFoundError(AppError):
    code = "SUBSCRIPTION_NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Subscription not found"


class InvalidSubscriptionOwnerError(AppError):
    code = "INVALID_SUBSCRIPTION_OWNER"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    message = "owner_user_id must be a member of the same household"


class InvalidSubscriptionCadenceError(AppError):
    code = "INVALID_SUBSCRIPTION_CADENCE"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    message = (
        "payment_month is required for yearly subscriptions and must be unset for monthly ones"
    )


def _validate_cadence(cadence: SubscriptionCadence, payment_month: int | None) -> None:
    if cadence == SubscriptionCadence.YEARLY and payment_month is None:
        raise InvalidSubscriptionCadenceError()
    if cadence == SubscriptionCadence.MONTHLY and payment_month is not None:
        raise InvalidSubscriptionCadenceError()


async def _resolve_income_user(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    creator_id: uuid.UUID,
    requested: uuid.UUID | None,
) -> uuid.UUID:
    if requested is None:
        return creator_id
    target = await session.get(User, requested)
    if target is None or target.tenant_id != tenant_id:
        raise InvalidIncomeOwnerError()
    return requested


async def _validate_subscription_owner(
    session: AsyncSession, *, tenant_id: uuid.UUID, requested: uuid.UUID | None
) -> None:
    if requested is None:
        return
    target = await session.get(User, requested)
    if target is None or target.tenant_id != tenant_id:
        raise InvalidSubscriptionOwnerError()


async def create_income(
    session: AsyncSession, *, tenant_id: uuid.UUID, creator_id: uuid.UUID, payload: IncomeCreate
) -> Income:
    user_id = await _resolve_income_user(
        session, tenant_id=tenant_id, creator_id=creator_id, requested=payload.user_id
    )
    income = Income(
        tenant_id=tenant_id,
        user_id=user_id,
        label=payload.label,
        amount=payload.amount,
        payment_day=payload.payment_day,
    )
    session.add(income)
    await session.flush()
    return income


async def get_income(
    session: AsyncSession, *, tenant_id: uuid.UUID, income_id: uuid.UUID
) -> Income:
    income = await session.get(Income, income_id)
    if income is None or income.tenant_id != tenant_id:
        raise IncomeNotFoundError()
    return income


async def list_incomes(
    session: AsyncSession, *, tenant_id: uuid.UUID, limit: int, offset: int
) -> tuple[list[Income], int]:
    query = (
        select(Income)
        .where(Income.tenant_id == tenant_id)
        .order_by(Income.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    count_query = select(func.count()).select_from(Income).where(Income.tenant_id == tenant_id)

    total = await session.scalar(count_query)
    items = list((await session.scalars(query)).all())
    return items, total or 0


async def update_income(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    creator_id: uuid.UUID,
    income_id: uuid.UUID,
    payload: IncomeUpdate,
) -> Income:
    income = await get_income(session, tenant_id=tenant_id, income_id=income_id)
    updates: dict[str, Any] = payload.model_dump(exclude_unset=True)

    if "user_id" in updates:
        updates["user_id"] = await _resolve_income_user(
            session, tenant_id=tenant_id, creator_id=creator_id, requested=updates["user_id"]
        )

    for field, value in updates.items():
        setattr(income, field, value)

    await session.flush()
    return income


async def delete_income(
    session: AsyncSession, *, tenant_id: uuid.UUID, income_id: uuid.UUID
) -> None:
    income = await get_income(session, tenant_id=tenant_id, income_id=income_id)
    await session.delete(income)
    await session.flush()


async def create_subscription(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    creator_id: uuid.UUID,
    payload: SubscriptionCreate,
) -> Subscription:
    await _validate_subscription_owner(
        session, tenant_id=tenant_id, requested=payload.owner_user_id
    )
    subscription = Subscription(
        tenant_id=tenant_id,
        created_by=creator_id,
        name=payload.name,
        amount=payload.amount,
        kind=payload.kind,
        cadence=payload.cadence,
        payment_day=payload.payment_day,
        payment_month=payload.payment_month,
        owner_user_id=payload.owner_user_id,
    )
    session.add(subscription)
    await session.flush()
    return subscription


async def get_subscription(
    session: AsyncSession, *, tenant_id: uuid.UUID, subscription_id: uuid.UUID
) -> Subscription:
    subscription = await session.get(Subscription, subscription_id)
    if subscription is None or subscription.tenant_id != tenant_id:
        raise SubscriptionNotFoundError()
    return subscription


async def list_subscriptions(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    active_only: bool,
    limit: int,
    offset: int,
) -> tuple[list[Subscription], int]:
    query = select(Subscription).where(Subscription.tenant_id == tenant_id)
    count_query = (
        select(func.count()).select_from(Subscription).where(Subscription.tenant_id == tenant_id)
    )
    if active_only:
        query = query.where(Subscription.active.is_(True))
        count_query = count_query.where(Subscription.active.is_(True))

    query = query.order_by(Subscription.payment_day, Subscription.created_at.desc())
    query = query.limit(limit).offset(offset)

    total = await session.scalar(count_query)
    items = list((await session.scalars(query)).all())
    return items, total or 0


async def update_subscription(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    subscription_id: uuid.UUID,
    payload: SubscriptionUpdate,
) -> Subscription:
    subscription = await get_subscription(
        session, tenant_id=tenant_id, subscription_id=subscription_id
    )
    updates: dict[str, Any] = payload.model_dump(exclude_unset=True)

    if "owner_user_id" in updates:
        await _validate_subscription_owner(
            session, tenant_id=tenant_id, requested=updates["owner_user_id"]
        )

    if "cadence" in updates or "payment_month" in updates:
        new_cadence = updates.get("cadence", subscription.cadence)
        new_payment_month = updates.get("payment_month", subscription.payment_month)
        _validate_cadence(new_cadence, new_payment_month)

    for field, value in updates.items():
        setattr(subscription, field, value)

    await session.flush()
    return subscription


async def delete_subscription(
    session: AsyncSession, *, tenant_id: uuid.UUID, subscription_id: uuid.UUID
) -> None:
    subscription = await get_subscription(
        session, tenant_id=tenant_id, subscription_id=subscription_id
    )
    await session.delete(subscription)
    await session.flush()
