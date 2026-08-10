import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.ai.factory import get_llm_provider
from home_manager.assistant import service as assistant_service
from home_manager.db.types import utcnow
from home_manager.integrations.alice.models import AliceLink
from home_manager.integrations.alice.security import generate_token, hash_token

NOT_LINKED_REPLY = "This device isn't linked to a Home Manager account yet."
EMPTY_UTTERANCE_REPLY = "Sorry, I didn't catch that."


async def create_or_replace_link(
    session: AsyncSession, *, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> str:
    """Issues a fresh webhook token for the user, invalidating any previous one."""
    raw_token = generate_token()
    existing = await session.scalar(select(AliceLink).where(AliceLink.user_id == user_id))
    if existing is not None:
        existing.token_hash = hash_token(raw_token)
        existing.last_used_at = None
    else:
        session.add(
            AliceLink(tenant_id=tenant_id, user_id=user_id, token_hash=hash_token(raw_token))
        )
    await session.flush()
    return raw_token


async def get_link_status(session: AsyncSession, *, user_id: uuid.UUID) -> AliceLink | None:
    link = await session.scalar(select(AliceLink).where(AliceLink.user_id == user_id))
    return link


async def revoke_link(session: AsyncSession, *, user_id: uuid.UUID) -> None:
    link = await get_link_status(session, user_id=user_id)
    if link is not None:
        await session.delete(link)
        await session.flush()


async def handle_webhook(session: AsyncSession, *, raw_token: str | None, utterance: str) -> str:
    """Turns one Alice webhook call into a reply string.

    Pure protocol adapter: tenant_id/user_id are resolved solely from the
    token (never from anything in the request body, which is untrusted
    input from Yandex's servers), and the actual work — interpreting the
    utterance and acting on it — is entirely delegated to
    home_manager.assistant.service, the same pipeline the in-app assistant
    chat uses. This module never touches tasks/calendar/etc. directly.
    """
    if not raw_token:
        return NOT_LINKED_REPLY

    link = await session.scalar(
        select(AliceLink).where(AliceLink.token_hash == hash_token(raw_token))
    )
    if link is None:
        return NOT_LINKED_REPLY

    link.last_used_at = utcnow()

    if not utterance.strip():
        await session.commit()
        return EMPTY_UTTERANCE_REPLY

    provider = get_llm_provider()
    intent = await assistant_service.interpret_message(provider, utterance)
    reply = await assistant_service.execute_intent(
        session, intent=intent, tenant_id=link.tenant_id, user_id=link.user_id
    )
    await session.commit()
    return reply.reply
