import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.auth.models import RefreshToken, Role, Tenant, User
from home_manager.auth.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from home_manager.config import get_settings
from home_manager.core.errors import AppError


class EmailAlreadyRegisteredError(AppError):
    code = "EMAIL_ALREADY_REGISTERED"
    status_code = status.HTTP_409_CONFLICT
    message = "An account with this email already exists"


class InvalidCredentialsError(AppError):
    code = "INVALID_CREDENTIALS"
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Invalid email or password"


class InvalidRefreshTokenError(AppError):
    code = "INVALID_REFRESH_TOKEN"
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Refresh token is invalid or expired"


@dataclass
class TokenPair:
    access_token: str
    expires_in: int
    refresh_token: str
    refresh_token_expires_at: datetime
    user: User


async def register_household(
    session: AsyncSession,
    *,
    household_name: str,
    display_name: str,
    email: str,
    password: str,
) -> User:
    """Create a new household (tenant) with the registering user as its owner."""
    existing = await session.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise EmailAlreadyRegisteredError()

    tenant = Tenant(name=household_name)
    session.add(tenant)
    await session.flush()

    user = User(
        tenant_id=tenant.id,
        email=email,
        display_name=display_name,
        hashed_password=hash_password(password),
        role=Role.OWNER,
    )
    session.add(user)
    await session.flush()
    return user


async def authenticate_user(session: AsyncSession, *, email: str, password: str) -> User:
    user = await session.scalar(select(User).where(User.email == email, User.is_active.is_(True)))
    if user is None or not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError()
    return user


async def issue_token_pair(
    session: AsyncSession, *, user: User, user_agent: str | None
) -> TokenPair:
    settings = get_settings()
    access_token, expires_in = create_access_token(
        user_id=str(user.id), tenant_id=str(user.tenant_id), role=user.role.value
    )
    raw_refresh_token = generate_refresh_token()
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)

    refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(raw_refresh_token),
        user_agent=user_agent[:300] if user_agent else None,
        expires_at=expires_at,
    )
    session.add(refresh_token)
    await session.flush()

    return TokenPair(
        access_token=access_token,
        expires_in=expires_in,
        refresh_token=raw_refresh_token,
        refresh_token_expires_at=expires_at,
        user=user,
    )


async def rotate_refresh_token(
    session: AsyncSession, *, raw_token: str, user_agent: str | None
) -> TokenPair:
    token_hash = hash_refresh_token(raw_token)
    stored = await session.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

    now = datetime.now(UTC)
    if stored is None or stored.revoked_at is not None or stored.expires_at < now:
        raise InvalidRefreshTokenError()

    user = await session.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise InvalidRefreshTokenError()

    new_pair = await issue_token_pair(session, user=user, user_agent=user_agent)

    new_token = await session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(new_pair.refresh_token)
        )
    )
    stored.revoked_at = now
    if new_token is not None:
        stored.replaced_by_id = new_token.id

    return new_pair


async def revoke_refresh_token(session: AsyncSession, *, raw_token: str) -> None:
    token_hash = hash_refresh_token(raw_token)
    stored = await session.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(UTC)


async def get_active_user(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return user
