from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.ai.factory import get_llm_provider
from home_manager.ai.provider import LLMProvider
from home_manager.assistant import service
from home_manager.assistant.schemas import AssistantMessageRequest, AssistantReply
from home_manager.auth.dependencies import get_current_user
from home_manager.auth.models import User
from home_manager.db.session import get_db_session
from home_manager.preferences import service as preferences_service

router = APIRouter(prefix="/assistant", tags=["assistant"])

CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
Provider = Annotated[LLMProvider, Depends(get_llm_provider)]


@router.post("/message", response_model=AssistantReply)
async def send_message(
    payload: AssistantMessageRequest,
    current_user: CurrentUser,
    session: DbSession,
    provider: Provider,
) -> AssistantReply:
    intent = await service.interpret_message(
        provider, payload.message, client_now=payload.client_now
    )
    prefs = await preferences_service.get_or_create_preferences(
        session, tenant_id=current_user.tenant_id, user_id=current_user.id
    )
    await session.commit()
    return await service.execute_intent(
        session,
        intent=intent,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        client_now=payload.client_now,
        locale=payload.locale,
        workplace=prefs.workplace,
    )
