import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.preferences.models import UserPreferences
from home_manager.preferences.schemas import PreferencesUpdate


async def get_or_create_preferences(
    session: AsyncSession, *, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> UserPreferences:
    prefs = await session.scalar(select(UserPreferences).where(UserPreferences.user_id == user_id))
    if prefs is not None:
        return prefs

    prefs = UserPreferences(tenant_id=tenant_id, user_id=user_id)
    session.add(prefs)
    await session.flush()
    return prefs


async def update_preferences(
    session: AsyncSession, *, tenant_id: uuid.UUID, user_id: uuid.UUID, payload: PreferencesUpdate
) -> UserPreferences:
    prefs = await get_or_create_preferences(session, tenant_id=tenant_id, user_id=user_id)
    updates: dict[str, Any] = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(prefs, field, value)
    await session.flush()
    return prefs
