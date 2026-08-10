from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.auth.dependencies import get_current_user
from home_manager.auth.models import User
from home_manager.db.session import get_db_session
from home_manager.preferences import service
from home_manager.preferences.schemas import PreferencesResponse, PreferencesUpdate

router = APIRouter(prefix="/preferences", tags=["preferences"])

CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/me", response_model=PreferencesResponse)
async def get_my_preferences(current_user: CurrentUser, session: DbSession) -> PreferencesResponse:
    prefs = await service.get_or_create_preferences(
        session, tenant_id=current_user.tenant_id, user_id=current_user.id
    )
    await session.commit()
    return PreferencesResponse.model_validate(prefs)


@router.patch("/me", response_model=PreferencesResponse)
async def update_my_preferences(
    payload: PreferencesUpdate, current_user: CurrentUser, session: DbSession
) -> PreferencesResponse:
    prefs = await service.update_preferences(
        session, tenant_id=current_user.tenant_id, user_id=current_user.id, payload=payload
    )
    await session.commit()
    return PreferencesResponse.model_validate(prefs)
