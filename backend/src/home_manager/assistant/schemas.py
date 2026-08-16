import re
import uuid
from decimal import Decimal
from typing import Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from home_manager.calendar.models import CalendarEventType
from home_manager.calendar.schemas import CalendarEventCreate
from home_manager.finance.models import SubscriptionCadence, SubscriptionKind


class CreateTaskIntent(BaseModel):
    intent: Literal["create_task"] = "create_task"
    title: str = Field(min_length=1, max_length=200)
    duration_minutes: int | None = Field(default=None, gt=0)


class ScheduleEventItem(BaseModel):
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    start_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    event_type: CalendarEventType
    title: str | None = Field(default=None, max_length=200)


class SchedulePattern(BaseModel):
    """A repeating weekday pattern over a date range.

    Deliberately not a list of dates — small models are unreliable at
    enumerating many dates by hand (tested: it silently dropped most of a
    month-long range). This shape only asks the model for ~6 short fields;
    service.py expands it into individual dates itself, the same
    deterministic way the calendar page's own bulk-schedule generator does.
    """

    weekdays: list[int] = Field(min_length=1, max_length=7)
    date_from: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    date_to: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    start_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    event_type: CalendarEventType
    title: str | None = Field(default=None, max_length=200)
    # Individual dates to skip within the range (e.g. "every weekday except
    # the 12th and 13th"). Without a real field for this, testing showed the
    # model would invent its own key name for it, which Pydantic silently
    # drops — the exclusion just vanished and every date got scheduled.
    exclude_dates: list[str] = Field(
        default_factory=list, max_length=60, examples=[["2026-08-12", "2026-08-13"]]
    )

    @field_validator("weekdays")
    @classmethod
    def _validate_weekdays(cls, value: list[int]) -> list[int]:
        if any(day < 1 or day > 7 for day in value):
            raise ValueError("weekdays must be ISO weekday numbers 1 (Mon) to 7 (Sun)")
        return sorted(set(value))

    @field_validator("exclude_dates")
    @classmethod
    def _validate_exclude_dates(cls, value: list[str]) -> list[str]:
        date_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        if any(not date_re.match(d) for d in value):
            raise ValueError("exclude_dates entries must be YYYY-MM-DD")
        return value


class RotationSchedulePattern(BaseModel):
    """An N-days-on / M-days-off rotating shift over a date range (e.g. a
    "2/2" or "3/3" schedule) — distinct from SchedulePattern, whose weekday
    list can't express a cycle that isn't aligned to the calendar week.
    Expanded the same deterministic way as the calendar page's own
    rotation-mode bulk generator (see BulkScheduleForm.tsx's handleGenerate).
    """

    work_days: int = Field(ge=1, le=31)
    off_days: int = Field(ge=0, le=31)
    date_from: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    date_to: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    start_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    event_type: CalendarEventType
    title: str | None = Field(default=None, max_length=200)


class CreateScheduleIntent(BaseModel):
    intent: Literal["create_schedule"] = "create_schedule"
    # Bounded the same as the calendar bulk-create endpoint it feeds into.
    events: list[ScheduleEventItem] = Field(default_factory=list, max_length=60)
    pattern: SchedulePattern | None = None
    rotation: RotationSchedulePattern | None = None

    @model_validator(mode="after")
    def _require_events_or_pattern(self) -> Self:
        if not self.events and self.pattern is None and self.rotation is None:
            raise ValueError("create_schedule requires events, a pattern, or a rotation")
        return self


class CreateIncomeIntent(BaseModel):
    intent: Literal["create_income"] = "create_income"
    label: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(gt=0)
    payment_day: int = Field(ge=1, le=31)
    # The household member's name as mentioned in the message ("Лена",
    # "Паша"), or null when the message is about the speaker's own income
    # ("я получаю", "моя зарплата") or doesn't name anyone — execute_intent
    # resolves this to a real user_id server-side, defaulting to the
    # speaker when null, the same way the Finance page's own form does.
    person: str | None = Field(default=None, max_length=100)


class CreateSubscriptionIntent(BaseModel):
    intent: Literal["create_subscription"] = "create_subscription"
    name: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(gt=0)
    kind: SubscriptionKind = SubscriptionKind.SUBSCRIPTION
    cadence: SubscriptionCadence = SubscriptionCadence.MONTHLY
    payment_day: int = Field(ge=1, le=31)
    payment_month: int | None = Field(default=None, ge=1, le=12)
    # Whose name it's under, as mentioned in the message — null when
    # unspecified, which stays unspecified (a shared/household item), never
    # defaults to the speaker (matches SubscriptionCreate.owner_user_id).
    owner: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def _validate_payment_month(self) -> Self:
        if self.cadence == SubscriptionCadence.YEARLY and self.payment_month is None:
            raise ValueError("payment_month is required for a yearly subscription")
        if self.cadence == SubscriptionCadence.MONTHLY and self.payment_month is not None:
            raise ValueError("payment_month must not be set for a monthly subscription")
        return self


class QueryFinanceSummaryIntent(BaseModel):
    intent: Literal["query_finance_summary"] = "query_finance_summary"


class UnknownIntent(BaseModel):
    intent: Literal["unknown"] = "unknown"
    raw_message: str
    # Set when the model attempted create_schedule but omitted a required
    # time field — lets execute_intent give a specific "you forgot the
    # time" reply instead of the generic unknown-intent one.
    reason: Literal["missing_time"] | None = None


AssistantIntent = (
    CreateTaskIntent
    | CreateScheduleIntent
    | CreateIncomeIntent
    | CreateSubscriptionIntent
    | QueryFinanceSummaryIntent
    | UnknownIntent
)


class AssistantMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    # ISO 8601 with UTC offset, e.g. "2026-08-10T22:30:00+03:00" — lets the
    # assistant resolve "tomorrow"/"Monday" and store shift times in the
    # user's actual local time instead of guessing a timezone server-side.
    client_now: str | None = Field(default=None, max_length=40)
    # The UI's current language ("en"/"ru") — only used to pick which fixed
    # reply strings execute_intent responds with, unrelated to what language
    # the user's own message happens to be in.
    locale: str = Field(default="en", max_length=10)


class AssistantReply(BaseModel):
    reply: str
    task_id: uuid.UUID | None = None
    # Parsed but not yet saved — the frontend shows these for the user to
    # review/trim, then submits them itself via the normal calendar bulk
    # endpoint. Nothing from a create_schedule intent is persisted directly
    # by the assistant; a small free LLM is not reliable enough for that.
    proposed_events: list[CalendarEventCreate] | None = None
