import json
import uuid
from datetime import UTC, date, datetime, timedelta

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.ai.provider import LLMProvider
from home_manager.assistant.schemas import (
    AssistantIntent,
    AssistantReply,
    CreateScheduleIntent,
    CreateTaskIntent,
    UnknownIntent,
)
from home_manager.calendar.schemas import CalendarEventCreate
from home_manager.tasks import service as tasks_service
from home_manager.tasks.schemas import TaskCreate


def _parse_client_now(client_now: str | None) -> tuple[datetime, str]:
    """Resolves the "current time" to interpret relative dates against.

    Falls back to server UTC "now" (offset "+00:00") when the client didn't
    send a reading, or sent one we can't parse — this only degrades the
    assistant's date math, it never breaks the request.
    """
    parsed: datetime | None = None
    if client_now:
        try:
            parsed = datetime.fromisoformat(client_now)
        except ValueError:
            parsed = None
    if parsed is None:
        parsed = datetime.now(UTC)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    raw_offset = parsed.strftime("%z") or "+0000"
    offset = f"{raw_offset[:3]}:{raw_offset[3:]}"
    return parsed, offset


def _build_date_lookup_table(now: datetime) -> str:
    """A 14-day date/weekday lookup table for the prompt.

    Small free models are unreliable at *computing* relative dates
    ("this week", "next Monday") from a single "today is ..." sentence —
    in testing, one miscounted "this week Mon-Fri" as next week's dates.
    Handing over every date already resolved turns that into a lookup,
    which is a much easier task than arithmetic for these models.
    """
    lines = []
    for i in range(14):
        d = (now + timedelta(days=i)).date()
        tag = " (today)" if i == 0 else " (tomorrow)" if i == 1 else ""
        lines.append(f"{d.isoformat()} = {d.strftime('%A')}{tag}")
    return "\n".join(lines)


def _build_system_prompt(now: datetime) -> str:
    return (
        "You are a household assistant. Read the user's message and reply with a single "
        "JSON object describing their intent, and nothing else.\n"
        "Here is a lookup table of dates and their weekday, in the user's own local "
        "timezone — use it directly to resolve any relative date "
        '("tomorrow", "next Monday", "this weekend"), never compute dates yourself:\n'
        f"{_build_date_lookup_table(now)}\n"
        'To create a single task: {"intent": "create_task", "title": "...", '
        '"duration_minutes": <int or null>}\n'
        "To record one or more calendar entries — a work shift, sleep schedule, a repeating "
        'pattern like "I work Mon-Fri 9 to 6" or "I\'m off Saturday and Sunday", or several '
        "shifts listed at once — expand every date the user implies into its own item and "
        'reply: {"intent": "create_schedule", "events": [{"date": "YYYY-MM-DD", '
        '"start_time": "HH:MM", "end_time": "HH:MM", "event_type": one of '
        '"working_hours"/"sleep"/"meeting"/"sport"/"trip"/"personal"/"unavailable", '
        '"title": "..." or null}]}\n'
        'Otherwise: {"intent": "unknown", "raw_message": "<the original message>"}'
    )


async def interpret_message(
    provider: LLMProvider, message: str, *, client_now: str | None = None
) -> AssistantIntent:
    """Turns free text into a validated, typed intent.

    The provider's raw output is untrusted: anything that isn't valid JSON,
    doesn't match a known intent shape, or fails Pydantic validation falls
    back to UnknownIntent rather than propagating a malformed intent further.
    """
    now, _offset = _parse_client_now(client_now)
    raw = await provider.complete(system_prompt=_build_system_prompt(now), user_message=message)

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return UnknownIntent(raw_message=message)

    if not isinstance(data, dict):
        return UnknownIntent(raw_message=message)

    intent_name = data.get("intent")
    if intent_name == "create_task":
        try:
            return CreateTaskIntent.model_validate(data)
        except ValidationError:
            return UnknownIntent(raw_message=message)
    if intent_name == "create_schedule":
        try:
            return CreateScheduleIntent.model_validate(data)
        except ValidationError:
            return UnknownIntent(raw_message=message)

    return UnknownIntent(raw_message=message)


def _default_schedule_title(event_type: str) -> str:
    return event_type.replace("_", " ").capitalize()


async def execute_intent(
    session: AsyncSession,
    *,
    intent: AssistantIntent,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    client_now: str | None = None,
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

    if isinstance(intent, CreateScheduleIntent):
        _, offset = _parse_client_now(client_now)
        try:
            items: list[CalendarEventCreate] = []
            for item in intent.events:
                end_date = item.date
                # Overnight shift: end time doesn't come after start time on
                # the same day, so it must roll into the next calendar day.
                if item.end_time <= item.start_time:
                    end_date = (date.fromisoformat(item.date) + timedelta(days=1)).isoformat()
                items.append(
                    CalendarEventCreate(
                        event_type=item.event_type,
                        title=item.title or _default_schedule_title(item.event_type),
                        start_at=f"{item.date}T{item.start_time}:00{offset}",
                        end_at=f"{end_date}T{item.end_time}:00{offset}",
                    )
                )
        except (ValidationError, ValueError):
            # The regex on ScheduleEventItem only checks digit shape, not
            # calendar validity (e.g. "2026-02-30") — a model the LLM
            # returned nonsense for degrades to a normal "didn't understand"
            # reply instead of a 500, same as any other unparseable output.
            return AssistantReply(
                reply=("I couldn't quite work out those dates — try rephrasing your schedule."),
                task_id=None,
            )

        # Deliberately not persisted here — see AssistantReply.proposed_events.
        # The caller reviews/trims this list and saves it via the normal
        # calendar bulk-create endpoint.
        return AssistantReply(
            reply=f"Here's what I understood — {len(items)} event(s). Check them and confirm.",
            proposed_events=items,
        )

    return AssistantReply(
        reply=(
            "Sorry, I didn't understand that. Try something like "
            '"create task: water the plants, 15 minutes", or describe your work schedule.'
        ),
        task_id=None,
    )
