from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.auth.dependencies import get_current_user
from home_manager.auth.models import User
from home_manager.db.session import get_db_session
from home_manager.integrations.alice import service
from home_manager.integrations.alice.schemas import AliceLinkStatusResponse, AliceTokenResponse

router = APIRouter(prefix="/integrations/alice", tags=["integrations"])

CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db_session)]

# Yandex Dialogs truncates/rejects overly long responses; stay well under
# the documented 1024-character limit.
MAX_REPLY_LENGTH = 1000


@router.get("/token", response_model=AliceLinkStatusResponse)
async def get_token_status(
    current_user: CurrentUser, session: DbSession
) -> AliceLinkStatusResponse:
    link = await service.get_link_status(session, user_id=current_user.id)
    return AliceLinkStatusResponse(
        linked=link is not None, last_used_at=link.last_used_at if link else None
    )


@router.post("/token", response_model=AliceTokenResponse)
async def issue_token(current_user: CurrentUser, session: DbSession) -> AliceTokenResponse:
    raw_token = await service.create_or_replace_link(
        session, tenant_id=current_user.tenant_id, user_id=current_user.id
    )
    await session.commit()
    return AliceTokenResponse(
        token=raw_token, webhook_url=f"/api/v1/integrations/alice/webhook?token={raw_token}"
    )


@router.delete("/token", status_code=status.HTTP_204_NO_CONTENT)
async def delete_token(current_user: CurrentUser, session: DbSession) -> None:
    await service.revoke_link(session, user_id=current_user.id)
    await session.commit()


@router.post("/webhook")
async def webhook(
    request: Request,
    session: DbSession,
    token: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    """Public endpoint that Yandex's servers call directly — never gated by
    our own session auth, since Alice can't send an Authorization header.
    The opaque `token` query param is the only trust boundary; see
    integrations/alice/service.handle_webhook.
    """
    body = await request.json()
    incoming_session = body.get("session") or {}
    version = body.get("version", "1.0")
    utterance = ((body.get("request") or {}).get("original_utterance")) or ""

    reply_text = await service.handle_webhook(session, raw_token=token, utterance=utterance)

    return {
        "response": {"text": reply_text[:MAX_REPLY_LENGTH], "end_session": False},
        "session": incoming_session,
        "version": version,
    }
