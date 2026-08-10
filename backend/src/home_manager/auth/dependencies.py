import uuid
from collections.abc import Callable, Coroutine
from typing import Annotated, Any

import jwt
from fastapi import Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.auth.models import Role, User
from home_manager.auth.security import decode_access_token
from home_manager.auth.service import get_active_user
from home_manager.core.errors import AppError
from home_manager.db.session import get_db_session


class NotAuthenticatedError(AppError):
    code = "NOT_AUTHENTICATED"
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Authentication required"


class InsufficientPermissionsError(AppError):
    code = "INSUFFICIENT_PERMISSIONS"
    status_code = status.HTTP_403_FORBIDDEN
    message = "You do not have permission to perform this action"


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise NotAuthenticatedError()
    return authorization.split(" ", 1)[1].strip()


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_db_session),
) -> User:
    token = _extract_bearer_token(authorization)
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError as exc:
        raise NotAuthenticatedError() from exc

    if payload.get("type") != "access":
        raise NotAuthenticatedError()

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise NotAuthenticatedError() from exc

    user = await get_active_user(session, user_id)
    if user is None:
        raise NotAuthenticatedError()

    return user


def require_role(*roles: Role) -> Callable[..., Coroutine[Any, Any, User]]:
    async def _dependency(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in roles:
            raise InsufficientPermissionsError()
        return current_user

    return _dependency
