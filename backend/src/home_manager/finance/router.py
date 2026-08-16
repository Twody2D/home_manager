import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.auth.dependencies import get_current_user
from home_manager.auth.models import User
from home_manager.db.session import get_db_session
from home_manager.finance import service
from home_manager.finance.schemas import (
    IncomeCreate,
    IncomeListResponse,
    IncomeResponse,
    IncomeUpdate,
    SubscriptionCreate,
    SubscriptionListResponse,
    SubscriptionResponse,
    SubscriptionUpdate,
)

router = APIRouter(prefix="/finance", tags=["finance"])

CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("/incomes", response_model=IncomeResponse, status_code=status.HTTP_201_CREATED)
async def create_income(
    payload: IncomeCreate, current_user: CurrentUser, session: DbSession
) -> IncomeResponse:
    income = await service.create_income(
        session, tenant_id=current_user.tenant_id, creator_id=current_user.id, payload=payload
    )
    await session.commit()
    return IncomeResponse.model_validate(income)


@router.get("/incomes", response_model=IncomeListResponse)
async def list_incomes(
    current_user: CurrentUser,
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> IncomeListResponse:
    items, total = await service.list_incomes(
        session, tenant_id=current_user.tenant_id, limit=limit, offset=offset
    )
    return IncomeListResponse(
        items=[IncomeResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/incomes/{income_id}", response_model=IncomeResponse)
async def get_income(
    income_id: uuid.UUID, current_user: CurrentUser, session: DbSession
) -> IncomeResponse:
    income = await service.get_income(
        session, tenant_id=current_user.tenant_id, income_id=income_id
    )
    return IncomeResponse.model_validate(income)


@router.patch("/incomes/{income_id}", response_model=IncomeResponse)
async def update_income(
    income_id: uuid.UUID, payload: IncomeUpdate, current_user: CurrentUser, session: DbSession
) -> IncomeResponse:
    income = await service.update_income(
        session,
        tenant_id=current_user.tenant_id,
        creator_id=current_user.id,
        income_id=income_id,
        payload=payload,
    )
    await session.commit()
    return IncomeResponse.model_validate(income)


@router.delete("/incomes/{income_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_income(
    income_id: uuid.UUID, current_user: CurrentUser, session: DbSession
) -> None:
    await service.delete_income(session, tenant_id=current_user.tenant_id, income_id=income_id)
    await session.commit()


@router.post(
    "/subscriptions", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED
)
async def create_subscription(
    payload: SubscriptionCreate, current_user: CurrentUser, session: DbSession
) -> SubscriptionResponse:
    subscription = await service.create_subscription(
        session, tenant_id=current_user.tenant_id, creator_id=current_user.id, payload=payload
    )
    await session.commit()
    return SubscriptionResponse.model_validate(subscription)


@router.get("/subscriptions", response_model=SubscriptionListResponse)
async def list_subscriptions(
    current_user: CurrentUser,
    session: DbSession,
    active_only: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SubscriptionListResponse:
    items, total = await service.list_subscriptions(
        session,
        tenant_id=current_user.tenant_id,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )
    return SubscriptionListResponse(
        items=[SubscriptionResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: uuid.UUID, current_user: CurrentUser, session: DbSession
) -> SubscriptionResponse:
    subscription = await service.get_subscription(
        session, tenant_id=current_user.tenant_id, subscription_id=subscription_id
    )
    return SubscriptionResponse.model_validate(subscription)


@router.patch("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: uuid.UUID,
    payload: SubscriptionUpdate,
    current_user: CurrentUser,
    session: DbSession,
) -> SubscriptionResponse:
    subscription = await service.update_subscription(
        session,
        tenant_id=current_user.tenant_id,
        subscription_id=subscription_id,
        payload=payload,
    )
    await session.commit()
    return SubscriptionResponse.model_validate(subscription)


@router.delete("/subscriptions/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    subscription_id: uuid.UUID, current_user: CurrentUser, session: DbSession
) -> None:
    await service.delete_subscription(
        session, tenant_id=current_user.tenant_id, subscription_id=subscription_id
    )
    await session.commit()
