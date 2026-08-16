import json
import re
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.ai.provider import LLMProvider
from home_manager.assistant.schemas import (
    AssistantIntent,
    AssistantReply,
    CreateIncomeIntent,
    CreateScheduleIntent,
    CreateSubscriptionIntent,
    CreateTaskIntent,
    QueryFinanceSummaryIntent,
    RotationSchedulePattern,
    ScheduleEventItem,
    SchedulePattern,
    UnknownIntent,
)
from home_manager.auth.models import User
from home_manager.calendar.schemas import CalendarEventCreate
from home_manager.finance import service as finance_service
from home_manager.finance.models import SubscriptionCadence, SubscriptionKind
from home_manager.finance.schemas import IncomeCreate, SubscriptionCreate
from home_manager.tasks import service as tasks_service
from home_manager.tasks.schemas import TaskCreate
from home_manager.users import service as users_service


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
        '"duration_minutes": <int or null>, "budget_amount": <number or null>, '
        '"budget_person": "<name>" or null}. budget_amount/budget_person are ONLY set when '
        'the task itself has money set aside for it ("купить подарок за 5000", "на ремонт '
        'выделено 20000, платит Лена") — budget_person names whose money it is, stays null '
        'for a shared/household budget, never defaults to the speaker. Example — "создай '
        'задачу купить подарок маме, бюджет 5000" → {"intent": "create_task", "title": '
        '"Купить подарок маме", "duration_minutes": null, "budget_amount": 5000, '
        '"budget_person": null}. Example — "Лена, купи продукты, бюджет 3000 с моей карты" '
        'said by Лена → {"intent": "create_task", "title": "Купить продукты", '
        '"duration_minutes": null, "budget_amount": 3000, "budget_person": "Лена"}.\n'
        "IMPORTANT — if the message is about MONEY (зарплата/salary, доход/income, "
        "подписка/subscription, аренда/rent, коммуналка/счётчики/utilities, or any "
        "regular payment), it is NEVER create_task and NEVER create_schedule, even if it "
        "mentions a day of the month — use ONE of these three shapes instead:\n"
        'M1) Someone receives regular money (a salary/income): {"intent": "create_income", '
        '"label": "...", "amount": <number>, "payment_day": <1-31>, "person": "<name>" or '
        "null}. person is null when the message is about the speaker's own money (\"я "
        'получаю", "моя зарплата", "у меня") or names no one; set it ONLY when a specific '
        'household member is named. No day mentioned → use 25. Example — "Лена получает '
        '30000 25 числа" → {"intent": "create_income", "label": "Зарплата", "amount": 30000, '
        '"payment_day": 25, "person": "Лена"}. Example — "я получаю зарплату 45000 25 числа" '
        '→ {"intent": "create_income", "label": "Зарплата", "amount": 45000, "payment_day": '
        '25, "person": null}.\n'
        'M2) A subscription or a household bill (rent/utilities) recurs: {"intent": '
        '"create_subscription", "name": "...", "amount": <number>, "kind": "subscription" or '
        '"recurring_expense", "cadence": "monthly" or "yearly", "payment_day": <1-31>, '
        '"payment_month": <1-12> (ONLY if cadence is "yearly", otherwise omit), "owner": '
        '"<name>" or null}. kind="subscription" is a named service (Netflix, Spotify, gym) — '
        'kind="recurring_expense" is a household bill that is not a named service (rent, '
        'utilities, electricity, water, internet, mortgage, insurance, "аренда", "коммуналка", '
        '"счётчики"). Rent and utilities are ALWAYS "recurring_expense", never "subscription". '
        "owner stays null unless a specific person's name is given — do not default it to the "
        'speaker. No day mentioned → use 1. Example — "добавь аренду квартиры 45000 в месяц, '
        'плачу 1 числа" → {"intent": "create_subscription", "name": "Аренда квартиры", '
        '"amount": 45000, "kind": "recurring_expense", "cadence": "monthly", "payment_day": 1, '
        '"owner": null}. Example — "подписка Нетфликс 599 в месяц 15 числа" → {"intent": '
        '"create_subscription", "name": "Netflix", "amount": 599, "kind": "subscription", '
        '"cadence": "monthly", "payment_day": 15, "owner": null}. Example — "раз в год плачу '
        'за домен 1200 в марте" → {"intent": "create_subscription", "name": "Домен", "amount": '
        '1200, "kind": "recurring_expense", "cadence": "yearly", "payment_month": 3, '
        '"payment_day": 1, "owner": null}.\n'
        "M3) A question about total household money (how much income/subscriptions/left over) "
        '— never compute it yourself, just recognize the question: {"intent": '
        '"query_finance_summary"}. Example — "сколько мы тратим на подписки" or "какой у нас '
        'доход" or "сколько денег остаётся" → {"intent": "query_finance_summary"}.\n'
        "For calendar entries (work/sleep/sport/trip/personal schedules — NOT money), use "
        "whichever of these three shapes fits the request:\n"
        '1) A repeating weekday pattern over a date range (e.g. "work Mon-Fri this month", '
        '"every weekday in August", "off Sat/Sun for the next 2 weeks") — do NOT enumerate '
        "every date yourself, reply with the pattern instead and let the range stand for "
        'itself: {"intent": "create_schedule", "pattern": {"weekdays": [1,2,3,4,5], '
        '"date_from": "YYYY-MM-DD", "date_to": "YYYY-MM-DD", "start_time": "HH:MM", '
        '"end_time": "HH:MM", "event_type": one of "working_hours"/"sleep"/"meeting"/'
        '"sport"/"trip"/"personal"/"unavailable", "title": "..." or null, '
        '"exclude_dates": ["YYYY-MM-DD", ...]}} '
        '(weekdays are ISO numbers: 1=Monday .. 7=Sunday). A range phrased as "Monday to '
        'Friday" (or "с понедельника по пятницу") is INCLUSIVE of both ends — that means '
        'weekdays: [1,2,3,4,5], Friday included, not [1,2,3,4]. "5/2" with no other detail '
        "means a standard Mon-Fri working week — use shape 1 (pattern) with weekdays "
        '[1,2,3,4,5]. Any OTHER N/M ratio ("2/2", "3/3", "4/2", ...) is a ROTATING shift '
        "that repeats every (N+M) days regardless of the calendar week — that is shape 3 "
        "below, never shape 1, since a fixed weekday list can't express a cycle that isn't "
        'aligned to Monday. "weekend"/"выходные" means Saturday and Sunday ONLY — weekdays '
        "[6,7], never Friday. "
        '"every day except the weekend" (or "каждый день кроме выходных") therefore means '
        "weekdays [1,2,3,4,5] with Friday included, same as Mon-Fri — do not drop Friday.\n"
        'Any date the user excludes ("except the 12th and 13th", "кроме 12 и 13") goes in '
        "exclude_dates as its own field — never invent a different field name for this, and "
        "never silently drop it.\n"
        "2) A handful of specific/irregular shifts on different dates (different times on "
        "each date, or only a couple of one-off dates named directly) — list each one "
        'explicitly: {"intent": "create_schedule", "events": [{"date": "YYYY-MM-DD", '
        '"start_time": "HH:MM", "end_time": "HH:MM", "event_type": one of '
        '"working_hours"/"sleep"/"meeting"/"sport"/"trip"/"personal"/"unavailable", '
        '"title": "..." or null}]}. Example — "работаю 11-го с 11 до 23, 12-го с 12 до 24" '
        "(different start/end times on each date, so this is shape 2, not a weekday pattern) "
        'means: {"intent": "create_schedule", "events": [{"date": "<the 11th, from the table '
        'above>", "start_time": "11:00", "end_time": "23:00", "event_type": "working_hours", '
        '"title": null}, {"date": "<the 12th, from the table above>", "start_time": "12:00", '
        '"end_time": "00:00", "event_type": "working_hours", "title": null}]}. Clock times only '
        'go up to "23:59" — midnight/end of day ("до 24", "до полуночи", "until midnight") is '
        'always written as end_time "00:00", never "24:00".\n'
        '3) A rotating N-days-on/M-days-off shift ("2/2", "3/3", a ratio other than '
        '"5/2") over a date range: {"intent": "create_schedule", "rotation": {"work_days": '
        '<N>, "off_days": <M>, "date_from": "YYYY-MM-DD", "date_to": "YYYY-MM-DD", '
        '"start_time": "HH:MM", "end_time": "HH:MM", "event_type": one of "working_hours"/'
        '"sleep"/"meeting"/"sport"/"trip"/"personal"/"unavailable", "title": "..." or null}}. '
        'date_from is the FIRST day of the FIRST work block (e.g. "starting from the 3rd" '
        'means date_from is the 3rd, from the table above). Example — "работаю 2/2 весь '
        'август начиная с 3го числа с 9 до 21" means: {"intent": "create_schedule", '
        '"rotation": {"work_days": 2, "off_days": 2, "date_from": "<the 3rd, from the table '
        'above, in August>", "date_to": "<the last day of August>", "start_time": "09:00", '
        '"end_time": "21:00", "event_type": "working_hours", "title": null}}.\n'
        "In all three shapes, start_time and end_time are REQUIRED — if the user's message "
        "doesn't say what time the shift starts and ends, do not guess a time and do not use "
        'any of the three shapes above; reply {"intent": "unknown", "raw_message": "<the '
        'original message>"} instead so they can be asked for it.\n'
        "Money math (totals, remaining budget) is always computed by the backend — you never "
        "do arithmetic yourself, only extract the numbers named in the message.\n"
        'Otherwise: {"intent": "unknown", "raw_message": "<the original message>"}'
    )


_WEEKEND_TERMS = ("выходн", "weekend")


def _mentions_weekend_exclusion(message: str) -> bool:
    lowered = message.lower()
    return any(term in lowered for term in _WEEKEND_TERMS)


_FULL_WORKWEEK = [1, 2, 3, 4, 5]


def _fix_weekend_exclusion(intent: CreateScheduleIntent, message: str) -> None:
    """Cloudflare's small model is unreliable at "every day except the
    weekend" — in testing it dropped Friday ([1,2,3,4]), and separately
    dropped Thursday and Friday too ([1,2,3]), from the same kind of
    request. Prompt wording alone (an explicit rule plus a worked example)
    didn't fix this reliably, and patching only the exact [1,2,3,4] case
    missed the second failure mode — so this corrects the general pattern
    instead: when the user's own message actually talks about the weekend
    and the model returned some non-empty subset of weekdays that excludes
    both weekend days but isn't already the full Mon-Fri week, that's this
    bug, not a deliberate partial-week request (nobody says "except the
    weekend" to mean "only Monday to Wednesday").
    """
    pattern = intent.pattern
    if pattern is None or not _mentions_weekend_exclusion(message):
        return
    weekdays = set(pattern.weekdays)
    if weekdays and weekdays < set(_FULL_WORKWEEK):
        pattern.weekdays = _FULL_WORKWEEK


_ORDINAL_DAY_RE = re.compile(r"\b(\d{1,2})-?(?:го|ого|е|ой)\b", re.IGNORECASE)


def _fix_ordinal_day_mismatch(intent: CreateScheduleIntent, message: str) -> None:
    """Cloudflare's small model is unreliable at mapping a bare ordinal day
    ("11-го", "12-го") to the matching row in the date lookup table — live
    testing showed it drifting the day-of-month by a few days (e.g. "11-го"
    became the 13th or the 15th) while keeping the month/year and the
    relative order between events correct. Only correct this when the
    message names exactly as many ordinal days, in order, as the model
    returned events for — that's the one case where we can be confident
    which day belongs to which event without guessing.
    """
    if not intent.events:
        return
    matches = _ORDINAL_DAY_RE.findall(message)
    if len(matches) != len(intent.events):
        return
    for day_str, event in zip(matches, intent.events, strict=True):
        day = int(day_str)
        if not 1 <= day <= 31:
            return
        try:
            current = date.fromisoformat(event.date)
            event.date = current.replace(day=day).isoformat()
        except ValueError:
            return


_RATIO_RE = re.compile(r"\b(\d{1,2})\s*/\s*(\d{1,2})\b")


def _fix_ratio_misclassified_as_workweek(intent: CreateScheduleIntent, message: str) -> None:
    """Cloudflare's small model treats any "N/M" ratio as meaning a plain
    Mon-Fri working week (shape 1), even when N/M isn't "5/2" — live testing
    showed "2/2" coming back as {"pattern": {"weekdays": [1,2,3,4,5], ...}}
    instead of the rotating shift (shape 3) it actually describes. When the
    message names a ratio other than 5/2 and the model returned exactly a
    full Mon-Fri pattern, convert it to the rotation it should have been —
    the date range/time/event_type/title the model already got right carry
    over unchanged, only the shape changes.
    """
    pattern = intent.pattern
    if pattern is None or intent.rotation is not None:
        return
    match = _RATIO_RE.search(message)
    if match is None:
        return
    work_days, off_days = int(match.group(1)), int(match.group(2))
    if (work_days, off_days) == (5, 2):
        return
    if set(pattern.weekdays) != set(_FULL_WORKWEEK):
        return
    intent.rotation = RotationSchedulePattern(
        work_days=work_days,
        off_days=off_days,
        date_from=pattern.date_from,
        date_to=pattern.date_to,
        start_time=pattern.start_time,
        end_time=pattern.end_time,
        event_type=pattern.event_type,
        title=pattern.title,
    )
    intent.pattern = None


def _has_degenerate_time(intent: CreateScheduleIntent) -> bool:
    """True when a schedule/pattern/rotation's start and end time are
    identical — never a legitimate shift (that's zero duration), and one
    thing Cloudflare's small model fabricates when the message didn't
    actually give a time and it guesses instead of asking, rather than
    following the prompt's instruction to reply "unknown" in that case.
    """
    if intent.pattern is not None and intent.pattern.start_time == intent.pattern.end_time:
        return True
    if intent.rotation is not None and intent.rotation.start_time == intent.rotation.end_time:
        return True
    return bool(intent.events) and all(item.start_time == item.end_time for item in intent.events)


_TIME_MENTION_RE = re.compile(
    r"\d{1,2}[:.]\d{2}"  # "09:00", "9.00"
    r"|\bс\s*\d{1,2}\b[^.]{0,15}?\b(?:до|-)\s*\d{1,2}\b"  # "с 9 до 18", "с 9-18"
    r"|\bfrom\s*\d{1,2}\b[^.]{0,15}?\bto\s*\d{1,2}\b",  # "from 9 to 6"
    re.IGNORECASE,
)


def _message_mentions_time(message: str) -> bool:
    """False when the user's own message has no time-like token at all.

    _has_degenerate_time alone isn't reliable — live testing found the
    model sometimes fabricates a *plausible-looking* time (e.g. "09:00" to
    "21:00") for a message that never gave one, rather than the degenerate
    same-time placeholder that check catches. Requiring the message itself
    to contain something that looks like a time closes that gap: a model
    can invent a fake time value, but it can't invent one that's actually
    present in the user's own text.
    """
    return bool(_TIME_MENTION_RE.search(message))


def _is_missing_time_error(exc: ValidationError) -> bool:
    """True when validation failed only because start_time/end_time was
    missing (the model attempted a schedule but left out a required time),
    as opposed to some other malformed field the user can't easily fix by
    just adding a time.
    """
    return all(
        error["type"] == "missing" and error["loc"][-1] in ("start_time", "end_time")
        for error in exc.errors()
    )


def _is_missing_field_error(exc: ValidationError, field: str) -> bool:
    """True when validation failed only because a single named field was
    missing — as opposed to some other malformed field.
    """
    errors = exc.errors()
    return bool(errors) and all(
        error["type"] == "missing" and error["loc"][-1] == field for error in errors
    )


def _names_match(mentioned: str, member_name: str) -> bool:
    """Loose name match tolerant of Russian grammatical case endings.

    A model asked to echo a name back from the message may return any case
    form ("Лена"/"Лены"/"Лене"/"Лену") depending on how the sentence was
    phrased — comparing full strings would miss all but the nominative
    case. Comparing a shared stem (member name minus its last couple of
    letters) catches the common cases without a full morphology library.
    """
    mentioned_norm = mentioned.strip().lower()
    member_norm = member_name.strip().lower()
    if not mentioned_norm or not member_norm:
        return False
    stem_len = max(3, len(member_norm) - 2)
    return mentioned_norm[:stem_len] == member_norm[:stem_len]


def _resolve_person(
    members: list[User], mentioned: str | None, *, default_to_creator: bool, creator_id: uuid.UUID
) -> uuid.UUID | None:
    """Maps a name the LLM echoed back from the message to a real user_id.

    Never trusts the LLM with an id directly — it only ever gets to name
    someone, and this is the one place that name is resolved against the
    household's actual members. No match falls back to the creator (income)
    or stays unset (subscription owner), never to a guess at who else it
    might have meant.
    """
    if mentioned is not None:
        for member in members:
            if _names_match(mentioned, member.display_name):
                return member.id
    return creator_id if default_to_creator else None


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
            schedule_intent = CreateScheduleIntent.model_validate(data)
        except ValidationError as exc:
            reason = "missing_time" if _is_missing_time_error(exc) else None
            return UnknownIntent(raw_message=message, reason=reason)
        _fix_weekend_exclusion(schedule_intent, message)
        _fix_ordinal_day_mismatch(schedule_intent, message)
        _fix_ratio_misclassified_as_workweek(schedule_intent, message)
        if _has_degenerate_time(schedule_intent) or not _message_mentions_time(message):
            return UnknownIntent(raw_message=message, reason="missing_time")
        return schedule_intent
    if intent_name == "create_income":
        try:
            return CreateIncomeIntent.model_validate(data)
        except ValidationError as exc:
            # The prompt tells the model to default to day 25 when the
            # message doesn't give one, but small models don't reliably
            # follow that — omitting the field entirely rather than filling
            # in the default is more common, so apply it here instead of
            # asking the user for something the prompt already answered.
            if _is_missing_field_error(exc, "payment_day"):
                try:
                    return CreateIncomeIntent.model_validate({**data, "payment_day": 25})
                except ValidationError:
                    pass
            return UnknownIntent(raw_message=message)
    if intent_name == "create_subscription":
        try:
            return CreateSubscriptionIntent.model_validate(data)
        except ValidationError as exc:
            if _is_missing_field_error(exc, "payment_day"):
                try:
                    return CreateSubscriptionIntent.model_validate({**data, "payment_day": 1})
                except ValidationError:
                    pass
            return UnknownIntent(raw_message=message)
    if intent_name == "query_finance_summary":
        return QueryFinanceSummaryIntent()

    return UnknownIntent(raw_message=message)


# Fixed reply strings execute_intent responds with, keyed by the UI locale
# the request came in with — separate from whatever language the user's own
# message happens to be in, which only the LLM ever has to understand.
_REPLY_TEXT = {
    "en": {
        "task_added": 'Added "{title}" to your tasks.',
        "schedule_proposed": (
            "Here's what I understood — {count} event(s). Check them and confirm."
        ),
        "schedule_parse_error": (
            "I couldn't quite work out those dates — try rephrasing your schedule."
        ),
        "unknown": (
            "Sorry, I didn't understand that. Try something like "
            '"create task: water the plants, 15 minutes", or describe your work schedule.'
        ),
        "missing_time": (
            "Looks like a schedule, but I couldn't find a start and end time — add one, "
            'e.g. "from 9 to 18", and try again.'
        ),
        "income_added": 'Added income "{label}" — {amount} on day {day} of the month.',
        "subscription_added": 'Added subscription "{name}" — {amount}.',
        "recurring_expense_added": 'Added recurring expense "{name}" — {amount}.',
        "finance_summary": (
            "Monthly income: {income}. Subscriptions: {subscriptions}. "
            "Recurring expenses: {recurring}. Left over: {remaining}."
        ),
        "finance_summary_empty": "No income, subscriptions, or recurring expenses recorded yet.",
    },
    "ru": {
        "task_added": "Добавил «{title}» в задачи.",
        "schedule_proposed": ("Вот что получилось — {count} событий. Проверьте и подтвердите."),
        "schedule_parse_error": (
            "Не удалось разобрать эти даты — попробуйте переформулировать график."
        ),
        "unknown": (
            "Не понял сообщение. Попробуйте что-то вроде «создай задачу: полить цветы, "
            "15 минут», или опишите свой рабочий график."
        ),
        "missing_time": (
            "Похоже на график, но не нашёл время начала и окончания — добавьте, например, "
            "«с 9 до 18», и попробуйте снова."
        ),
        "income_added": "Добавил доход «{label}» — {amount}, {day} числа.",
        "subscription_added": "Добавил подписку «{name}» — {amount}.",
        "recurring_expense_added": "Добавил регулярный расход «{name}» — {amount}.",
        "finance_summary": (
            "Доход в месяц: {income}. Подписки: {subscriptions}. "
            "Регулярные расходы: {recurring}. Остаётся: {remaining}."
        ),
        "finance_summary_empty": "Доходы, подписки и регулярные расходы пока не внесены.",
    },
}

_EVENT_TYPE_LABELS = {
    "en": {
        "working_hours": "Working hours",
        "sleep": "Sleep",
        "meeting": "Meeting",
        "sport": "Sport",
        "trip": "Trip",
        "personal": "Personal",
        "unavailable": "Unavailable",
    },
    "ru": {
        "working_hours": "Работа",
        "sleep": "Сон",
        "meeting": "Встреча",
        "sport": "Спорт",
        "trip": "Поездка",
        "personal": "Личное",
        "unavailable": "Недоступен",
    },
}


def _reply_text(locale: str, key: str, **kwargs: object) -> str:
    lang = locale if locale in _REPLY_TEXT else "en"
    return _REPLY_TEXT[lang][key].format(**kwargs)


def _format_amount(amount: object) -> str:
    return f"{Decimal(str(amount)):.2f} ₽"


def _default_schedule_title(event_type: str, locale: str, *, workplace: str | None = None) -> str:
    lang = locale if locale in _EVENT_TYPE_LABELS else "en"
    label = _EVENT_TYPE_LABELS[lang].get(event_type, event_type.replace("_", " ").capitalize())
    if event_type == "working_hours" and workplace:
        return f"{label} — {workplace}"
    return label


def _expand_pattern(pattern: SchedulePattern) -> list[ScheduleEventItem]:
    """Turns a weekday/range pattern into one item per matching date.

    Plain date iteration, done here instead of by the LLM — see
    SchedulePattern's docstring for why.
    """
    start = date.fromisoformat(pattern.date_from)
    end = date.fromisoformat(pattern.date_to)
    excluded = set(pattern.exclude_dates)
    items: list[ScheduleEventItem] = []
    cursor = start
    while cursor <= end:
        if cursor.isoweekday() in pattern.weekdays and cursor.isoformat() not in excluded:
            items.append(
                ScheduleEventItem(
                    date=cursor.isoformat(),
                    start_time=pattern.start_time,
                    end_time=pattern.end_time,
                    event_type=pattern.event_type,
                    title=pattern.title,
                )
            )
        cursor += timedelta(days=1)
    return items


def _expand_rotation(pattern: RotationSchedulePattern) -> list[ScheduleEventItem]:
    """Turns an N-on/M-off rotating pattern into one item per work day.

    Mirrors BulkScheduleForm.tsx's handleGenerate (rotation mode) exactly:
    day offset from date_from, modulo the cycle length, is a work day when
    it falls in the first work_days of the cycle.
    """
    start = date.fromisoformat(pattern.date_from)
    end = date.fromisoformat(pattern.date_to)
    cycle_length = pattern.work_days + pattern.off_days
    items: list[ScheduleEventItem] = []
    if cycle_length <= 0:
        return items
    cursor = start
    while cursor <= end:
        if (cursor - start).days % cycle_length < pattern.work_days:
            items.append(
                ScheduleEventItem(
                    date=cursor.isoformat(),
                    start_time=pattern.start_time,
                    end_time=pattern.end_time,
                    event_type=pattern.event_type,
                    title=pattern.title,
                )
            )
        cursor += timedelta(days=1)
    return items


async def execute_intent(
    session: AsyncSession,
    *,
    intent: AssistantIntent,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    client_now: str | None = None,
    locale: str = "en",
    workplace: str | None = None,
) -> AssistantReply:
    """Runs an already-validated intent through real business logic.

    tenant_id/user_id always come from the caller's authenticated session,
    never from anything the LLM produced, so no intent can act outside the
    requesting user's own household — the LLM only chooses *what* to do,
    normal service-layer authorization decides whether it's allowed.
    """
    if isinstance(intent, CreateTaskIntent):
        budget_owner_id = None
        if intent.budget_person is not None:
            members = await users_service.list_members(session, tenant_id=tenant_id)
            budget_owner_id = _resolve_person(
                members, intent.budget_person, default_to_creator=False, creator_id=user_id
            )
        task = await tasks_service.create_task(
            session,
            tenant_id=tenant_id,
            created_by=user_id,
            payload=TaskCreate(
                title=intent.title,
                assigned_to=user_id,
                duration_minutes=intent.duration_minutes,
                budget_amount=intent.budget_amount,
                budget_owner_user_id=budget_owner_id,
            ),
        )
        await session.commit()
        return AssistantReply(
            reply=_reply_text(locale, "task_added", title=task.title), task_id=task.id
        )

    if isinstance(intent, CreateScheduleIntent):
        _, offset = _parse_client_now(client_now)
        try:
            schedule_items = list(intent.events)
            if intent.pattern is not None:
                schedule_items.extend(_expand_pattern(intent.pattern))
            if intent.rotation is not None:
                schedule_items.extend(_expand_rotation(intent.rotation))

            items: list[CalendarEventCreate] = []
            for item in schedule_items:
                end_date = item.date
                # "24:00" isn't a real clock time, but the prompt only asks
                # the model not to emit it — it isn't rejected by the schema
                # (the field is just a digit-shape regex), so normalize it
                # here too in case a model emits it anyway.
                end_time = "00:00" if item.end_time == "24:00" else item.end_time
                # Overnight shift: end time doesn't come after start time on
                # the same day, so it must roll into the next calendar day.
                if end_time <= item.start_time:
                    end_date = (date.fromisoformat(item.date) + timedelta(days=1)).isoformat()
                items.append(
                    CalendarEventCreate(
                        event_type=item.event_type,
                        title=item.title
                        or _default_schedule_title(item.event_type, locale, workplace=workplace),
                        start_at=f"{item.date}T{item.start_time}:00{offset}",
                        end_at=f"{end_date}T{end_time}:00{offset}",
                    )
                )
        except (ValidationError, ValueError):
            # The regex on ScheduleEventItem only checks digit shape, not
            # calendar validity (e.g. "2026-02-30") — a model the LLM
            # returned nonsense for degrades to a normal "didn't understand"
            # reply instead of a 500, same as any other unparseable output.
            return AssistantReply(reply=_reply_text(locale, "schedule_parse_error"), task_id=None)

        if not items:
            return AssistantReply(reply=_reply_text(locale, "schedule_parse_error"), task_id=None)

        # The confirm step submits this list as-is to the calendar bulk-create
        # endpoint, which caps a single request at 60 events — trim here too
        # so an oversized range (e.g. several months) doesn't 422 on confirm.
        items = items[:60]

        # Deliberately not persisted here — see AssistantReply.proposed_events.
        # The caller reviews/trims this list and saves it via the normal
        # calendar bulk-create endpoint.
        return AssistantReply(
            reply=_reply_text(locale, "schedule_proposed", count=len(items)),
            proposed_events=items,
        )

    if isinstance(intent, CreateIncomeIntent):
        members = await users_service.list_members(session, tenant_id=tenant_id)
        target_user_id = _resolve_person(
            members, intent.person, default_to_creator=True, creator_id=user_id
        )
        assert target_user_id is not None  # default_to_creator=True guarantees this
        income = await finance_service.create_income(
            session,
            tenant_id=tenant_id,
            creator_id=user_id,
            payload=IncomeCreate(
                user_id=target_user_id,
                label=intent.label,
                amount=intent.amount,
                payment_day=intent.payment_day,
            ),
        )
        await session.commit()
        return AssistantReply(
            reply=_reply_text(
                locale,
                "income_added",
                label=income.label,
                amount=_format_amount(income.amount),
                day=income.payment_day,
            ),
            task_id=None,
        )

    if isinstance(intent, CreateSubscriptionIntent):
        members = await users_service.list_members(session, tenant_id=tenant_id)
        owner_id = _resolve_person(
            members, intent.owner, default_to_creator=False, creator_id=user_id
        )
        subscription = await finance_service.create_subscription(
            session,
            tenant_id=tenant_id,
            creator_id=user_id,
            payload=SubscriptionCreate(
                name=intent.name,
                amount=intent.amount,
                kind=intent.kind,
                cadence=intent.cadence,
                payment_day=intent.payment_day,
                payment_month=intent.payment_month,
                owner_user_id=owner_id,
            ),
        )
        await session.commit()
        reply_key = (
            "recurring_expense_added"
            if intent.kind == SubscriptionKind.RECURRING_EXPENSE
            else "subscription_added"
        )
        return AssistantReply(
            reply=_reply_text(
                locale,
                reply_key,
                name=subscription.name,
                amount=_format_amount(subscription.amount),
            ),
            task_id=None,
        )

    if isinstance(intent, QueryFinanceSummaryIntent):
        incomes, _ = await finance_service.list_incomes(
            session, tenant_id=tenant_id, limit=100, offset=0
        )
        subscriptions, _ = await finance_service.list_subscriptions(
            session, tenant_id=tenant_id, active_only=True, limit=100, offset=0
        )
        if not incomes and not subscriptions:
            return AssistantReply(reply=_reply_text(locale, "finance_summary_empty"), task_id=None)

        def _monthly_equivalent(amount: object, cadence: SubscriptionCadence) -> Decimal:
            # Normalized via str() rather than trusting the caller's static
            # type — finance/models.py declares these Numeric columns as
            # Mapped[float], but asyncpg actually hands back Decimal at
            # runtime, and str() round-trips either one exactly.
            value = Decimal(str(amount))
            return value / 12 if cadence == SubscriptionCadence.YEARLY else value

        total_income: Decimal = sum((Decimal(str(i.amount)) for i in incomes), Decimal("0"))
        total_subscriptions: Decimal = sum(
            (
                _monthly_equivalent(s.amount, s.cadence)
                for s in subscriptions
                if s.kind == SubscriptionKind.SUBSCRIPTION
            ),
            Decimal("0"),
        )
        total_recurring: Decimal = sum(
            (
                _monthly_equivalent(s.amount, s.cadence)
                for s in subscriptions
                if s.kind == SubscriptionKind.RECURRING_EXPENSE
            ),
            Decimal("0"),
        )
        remaining = total_income - total_subscriptions - total_recurring
        return AssistantReply(
            reply=_reply_text(
                locale,
                "finance_summary",
                income=_format_amount(total_income),
                subscriptions=_format_amount(total_subscriptions),
                recurring=_format_amount(total_recurring),
                remaining=_format_amount(remaining),
            ),
            task_id=None,
        )

    if isinstance(intent, UnknownIntent) and intent.reason == "missing_time":
        return AssistantReply(reply=_reply_text(locale, "missing_time"), task_id=None)

    return AssistantReply(reply=_reply_text(locale, "unknown"), task_id=None)
