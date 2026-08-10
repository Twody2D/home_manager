import json
import uuid

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.ai.provider import LLMProvider
from home_manager.assistant.schemas import (
    AssistantIntent,
    AssistantReply,
    CreateTaskIntent,
    UnknownIntent,
)
from home_manager.tasks import service as tasks_service
from home_manager.tasks.schemas import TaskCreate

SYSTEM_PROMPT = (
    "You are a household task assistant. Read the user's message and reply with a single "
    "JSON object describing their intent, and nothing else.\n"
    'To create a task: {"intent": "create_task", "title": "...", '
    '"duration_minutes": <int or null>}\n'
    'Otherwise: {"intent": "unknown", "raw_message": "<the original message>"}'
)


async def interpret_message(provider: LLMProvider, message: str) -> AssistantIntent:
    """Turns free text into a validated, typed intent.

    The provider's raw output is untrusted: anything that isn't valid JSON,
    doesn't match a known intent shape, or fails Pydantic validation falls
    back to UnknownIntent rather than propagating a malformed intent further.
    """
    raw = await provider.complete(system_prompt=SYSTEM_PROMPT, user_message=message)

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return UnknownIntent(raw_message=message)

    if isinstance(data, dict) and data.get("intent") == "create_task":
        try:
            return CreateTaskIntent.model_validate(data)
        except ValidationError:
            return UnknownIntent(raw_message=message)

    return UnknownIntent(raw_message=message)


async def execute_intent(
    session: AsyncSession,
    *,
    intent: AssistantIntent,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> AssistantReply:
    """Runs an already-validated intent through real business logic.

    tenant_id/user_id always come from the caller's authenticated session,
    never from anything the LLM produced, so no intent can act outside the
    requesting user's own household — the LLM only chooses *what* to do,
    normal service-layer authorization decides whether it's allowed.
    """
    if isinstance(intent, CreateTaskIntent):
        task = await tasks_service.create_task(
            session,
            tenant_id=tenant_id,
            created_by=user_id,
            payload=TaskCreate(
                title=intent.title,
                assigned_to=user_id,
                duration_minutes=intent.duration_minutes,
            ),
        )
        await session.commit()
        return AssistantReply(reply=f'Added "{task.title}" to your tasks.', task_id=task.id)

    return AssistantReply(
        reply=(
            "Sorry, I didn't understand that. Try something like "
            '"create task: water the plants, 15 minutes".'
        ),
        task_id=None,
    )
