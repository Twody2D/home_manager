from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.auth.dependencies import get_current_user
from home_manager.auth.models import User
from home_manager.db.session import get_db_session
from home_manager.notifications import service
from home_manager.notifications.schemas import (
    PushSubscriptionCreate,
    TestNotificationResponse,
    VapidPublicKeyResponse,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])

CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/vapid-public-key", response_model=VapidPublicKeyResponse)
async def get_vapid_public_key(current_user: CurrentUser) -> VapidPublicKeyResponse:
    return VapidPublicKeyResponse(public_key=service.get_vapid_public_key())


@router.post("/subscriptions", status_code=status.HTTP_204_NO_CONTENT)
async def create_subscription(
    payload: PushSubscriptionCreate,
    current_user: CurrentUser,
    session: DbSession,
    request: Request,
) -> None:
    await service.subscribe(
        session,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        user_agent=request.headers.get("user-agent"),
        payload=payload,
    )
    await session.commit()


@router.delete("/subscriptions", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    current_user: CurrentUser,
    session: DbSession,
    endpoint: Annotated[str, Query(min_length=1, max_length=1000)],
) -> None:
    await service.unsubscribe(
        session, tenant_id=current_user.tenant_id, user_id=current_user.id, endpoint=endpoint
    )
    await session.commit()


@router.post("/test", response_model=TestNotificationResponse)
async def send_test_notification(
    current_user: CurrentUser, session: DbSession
) -> TestNotificationResponse:
    sent = await service.send_push(
        session,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        title="Home Manager",
        body="This is a test notification.",
    )
    return TestNotificationResponse(sent=sent)
