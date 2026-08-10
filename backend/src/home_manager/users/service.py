import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.auth.models import Role, User
from home_manager.auth.security import hash_password
from home_manager.auth.service import EmailAlreadyRegisteredError


async def list_members(session: AsyncSession, *, tenant_id: uuid.UUID) -> list[User]:
    result = await session.scalars(
        select(User).where(User.tenant_id == tenant_id).order_by(User.created_at)
    )
    return list(result.all())


async def invite_member(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    email: str,
    display_name: str,
    password: str,
    role: Role,
) -> User:
    existing = await session.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise EmailAlreadyRegisteredError()

    user = User(
        tenant_id=tenant_id,
        email=email,
        display_name=display_name,
        hashed_password=hash_password(password),
        role=role,
    )
    session.add(user)
    await session.flush()
    return user
