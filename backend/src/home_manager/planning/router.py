from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.auth.dependencies import get_current_user
from home_manager.auth.models import User
from home_manager.db.session import get_db_session
from home_manager.planning.engine import build_daily_plan
from home_manager.planning.schemas import DailyPlanResponse

router = APIRouter(prefix="/planning", tags=["planning"])

CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/plan", response_model=DailyPlanResponse)
async def get_daily_plan(
    current_user: CurrentUser,
    session: DbSession,
    plan_date: Annotated[date | None, Query(alias="date")] = None,
) -> DailyPlanResponse:
    target_date = plan_date or datetime.now(UTC).date()
    plan = await build_daily_plan(
        session, tenant_id=current_user.tenant_id, user_id=current_user.id, plan_date=target_date
    )
    await session.commit()
    return plan
