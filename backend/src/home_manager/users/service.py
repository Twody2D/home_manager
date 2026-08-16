import uuid
from datetime import UTC, datetime, timedelta

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.auth.models import Gender, MemberInvite, Role, Tenant, User
from home_manager.auth.security import generate_invite_token, hash_invite_token, hash_password
from home_manager.auth.service import EmailAlreadyRegisteredError
from home_manager.core.errors import AppError

INVITE_TTL = timedelta(hours=48)


class InvalidInviteError(AppError):
    code = "INVALID_INVITE"
    status_code = status.HTTP_404_NOT_FOUND
    message = "This invite link is invalid, expired, or already used"


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


async def create_invite(
    session: AsyncSession, *, tenant_id: uuid.UUID, created_by: uuid.UUID, role: Role = Role.MEMBER
) -> tuple[MemberInvite, str]:
    raw_token = generate_invite_token()
    invite = MemberInvite(
        tenant_id=tenant_id,
        created_by=created_by,
        token_hash=hash_invite_token(raw_token),
        role=role,
        expires_at=datetime.now(UTC) + INVITE_TTL,
    )
    session.add(invite)
    await session.flush()
    return invite, raw_token


async def _get_valid_invite(session: AsyncSession, *, raw_token: str) -> MemberInvite:
    invite = await session.scalar(
        select(MemberInvite).where(MemberInvite.token_hash == hash_invite_token(raw_token))
    )
    if invite is None or invite.used_at is not None or invite.expires_at < datetime.now(UTC):
        raise InvalidInviteError()
    return invite


async def preview_invite(session: AsyncSession, *, raw_token: str) -> tuple[MemberInvite, str]:
    invite = await _get_valid_invite(session, raw_token=raw_token)
    tenant = await session.get(Tenant, invite.tenant_id)
    tenant_name = (tenant.display_name or tenant.name) if tenant is not None else ""
    return invite, tenant_name


async def get_household(session: AsyncSession, *, tenant_id: uuid.UUID) -> Tenant:
    tenant = await session.get(Tenant, tenant_id)
    assert tenant is not None  # tenant_id always comes from an authenticated user's own token
    return tenant


async def update_household_display_name(
    session: AsyncSession, *, tenant_id: uuid.UUID, display_name: str | None
) -> Tenant:
    tenant = await get_household(session, tenant_id=tenant_id)
    tenant.display_name = display_name.strip() or None if display_name is not None else None
    await session.flush()
    return tenant


async def update_me(
    session: AsyncSession, *, user_id: uuid.UUID, display_name: str, gender: Gender | None
) -> User:
    user = await session.get(User, user_id)
    assert user is not None  # user_id always comes from an authenticated user's own token
    user.display_name = display_name.strip()
    if gender is not None:
        user.gender = gender
    await session.flush()
    return user


async def redeem_invite(
    session: AsyncSession, *, raw_token: str, email: str, display_name: str, password: str
) -> User:
    invite = await _get_valid_invite(session, raw_token=raw_token)
    user = await invite_member(
        session,
        tenant_id=invite.tenant_id,
        email=email,
        display_name=display_name,
        password=password,
        role=invite.role,
    )
    invite.used_at = datetime.now(UTC)
    return user
