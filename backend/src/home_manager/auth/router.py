from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.auth import service
from home_manager.auth.dependencies import get_current_user
from home_manager.auth.models import User
from home_manager.auth.rate_limit import login_rate_limiter
from home_manager.auth.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from home_manager.auth.security import generate_csrf_token
from home_manager.config import get_settings
from home_manager.core.errors import AppError
from home_manager.db.session import get_db_session
from home_manager.users import service as users_service
from home_manager.users.schemas import InviteRedeemRequest

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "refresh_token"
CSRF_COOKIE_NAME = "csrf_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"
# The CSRF cookie must be readable via document.cookie from wherever the SPA
# runs (any frontend route), so the client can echo it back as the
# X-CSRF-Token header — unlike the HttpOnly refresh cookie, it can't be
# scoped down to just the auth endpoints.
CSRF_COOKIE_PATH = "/"


class CsrfTokenMismatchError(AppError):
    code = "CSRF_TOKEN_MISMATCH"
    status_code = status.HTTP_403_FORBIDDEN
    message = "CSRF token missing or invalid"


class RegistrationClosedError(AppError):
    code = "REGISTRATION_CLOSED"
    status_code = status.HTTP_403_FORBIDDEN
    message = "Registration is currently closed"


def _set_auth_cookies(
    response: Response, *, refresh_token: str, refresh_expires_at: datetime, csrf_token: str
) -> None:
    settings = get_settings()
    secure = settings.environment != "development"
    max_age = max(0, int((refresh_expires_at - datetime.now(UTC)).total_seconds()))

    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=max_age,
        httponly=True,
        secure=secure,
        samesite="strict",
        path=REFRESH_COOKIE_PATH,
    )
    # Not HttpOnly on purpose: the frontend reads this to echo it back as the
    # X-CSRF-Token header (double-submit pattern) when calling /refresh and /logout.
    response.set_cookie(
        CSRF_COOKIE_NAME,
        csrf_token,
        max_age=max_age,
        httponly=False,
        secure=secure,
        samesite="strict",
        path=CSRF_COOKIE_PATH,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)
    response.delete_cookie(CSRF_COOKIE_NAME, path=CSRF_COOKIE_PATH)


async def _issue_tokens_and_respond(
    session: AsyncSession, response: Response, *, user: User, user_agent: str | None
) -> TokenResponse:
    token_pair = await service.issue_token_pair(session, user=user, user_agent=user_agent)
    await session.commit()

    _set_auth_cookies(
        response,
        refresh_token=token_pair.refresh_token,
        refresh_expires_at=token_pair.refresh_token_expires_at,
        csrf_token=generate_csrf_token(),
    )
    return TokenResponse(
        access_token=token_pair.access_token,
        expires_in=token_pair.expires_in,
        user=UserResponse.model_validate(user),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    response: Response,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    if not get_settings().registration_open:
        raise RegistrationClosedError()
    user = await service.register_household(
        session,
        household_name=payload.household_name,
        display_name=payload.display_name,
        email=payload.email,
        password=payload.password,
    )
    return await _issue_tokens_and_respond(
        session, response, user=user, user_agent=request.headers.get("user-agent")
    )


@router.post("/invites/{token}/redeem", response_model=TokenResponse)
async def redeem_invite(
    token: str,
    payload: InviteRedeemRequest,
    response: Response,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    user = await users_service.redeem_invite(
        session,
        raw_token=token,
        email=payload.email,
        display_name=payload.display_name,
        password=payload.password,
    )
    await session.commit()
    return await _issue_tokens_and_respond(
        session, response, user=user, user_agent=request.headers.get("user-agent")
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_key = f"{client_ip}:{payload.email.lower()}"
    login_rate_limiter.check(rate_limit_key)

    try:
        user = await service.authenticate_user(
            session, email=payload.email, password=payload.password
        )
    except service.InvalidCredentialsError:
        login_rate_limiter.record_failure(rate_limit_key)
        raise

    login_rate_limiter.reset(rate_limit_key)

    return await _issue_tokens_and_respond(
        session, response, user=user, user_agent=request.headers.get("user-agent")
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    request: Request,
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)] = None,
    csrf_cookie: Annotated[str | None, Cookie(alias=CSRF_COOKIE_NAME)] = None,
    x_csrf_token: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    if refresh_token is None:
        raise service.InvalidRefreshTokenError()
    if not csrf_cookie or not x_csrf_token or csrf_cookie != x_csrf_token:
        raise CsrfTokenMismatchError()

    token_pair = await service.rotate_refresh_token(
        session, raw_token=refresh_token, user_agent=request.headers.get("user-agent")
    )
    await session.commit()

    _set_auth_cookies(
        response,
        refresh_token=token_pair.refresh_token,
        refresh_expires_at=token_pair.refresh_token_expires_at,
        csrf_token=generate_csrf_token(),
    )
    return TokenResponse(
        access_token=token_pair.access_token,
        expires_in=token_pair.expires_in,
        user=UserResponse.model_validate(token_pair.user),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)] = None,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    if refresh_token is not None:
        await service.revoke_refresh_token(session, raw_token=refresh_token)
        await session.commit()
    _clear_auth_cookies(response)


@router.get("/me", response_model=UserResponse)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return UserResponse.model_validate(current_user)
