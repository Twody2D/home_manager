import json
import re

_DURATION_RE = re.compile(r"(\d+)\s*(?:min|minutes?|мин\w*)")
_CREATE_TASK_PREFIX_RE = re.compile(
    r"^(create task|add task|remind me to|new task)\s*:?\s*", re.IGNORECASE
)
_BUDGET_RE = re.compile(r"budget=(?P<amount>[\d.]+)(?:\s+budget_person=(?P<person>\S+))?")
_SCHEDULE_PREFIX_RE = re.compile(r"^schedule\s*:\s*", re.IGNORECASE)
_SCHEDULE_ITEM_RE = re.compile(
    r"(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<start>\d{2}:\d{2})-(?P<end>\d{2}:\d{2})\s+(?P<type>\w+)"
)
_PATTERN_PREFIX_RE = re.compile(r"^pattern\s*:\s*", re.IGNORECASE)
_PATTERN_RE = re.compile(
    r"weekdays=(?P<weekdays>[\d,]+)\s+from=(?P<from>\d{4}-\d{2}-\d{2})\s+"
    r"to=(?P<to>\d{4}-\d{2}-\d{2})\s+(?P<start>\d{2}:\d{2})-(?P<end>\d{2}:\d{2})\s+(?P<type>\w+)"
    r"(?:\s+exclude=(?P<exclude>[\d,-]+))?"
)
_ROTATION_PREFIX_RE = re.compile(r"^rotation\s*:\s*", re.IGNORECASE)
_ROTATION_RE = re.compile(
    r"work=(?P<work>\d+)\s+off=(?P<off>\d+)\s+from=(?P<from>\d{4}-\d{2}-\d{2})\s+"
    r"to=(?P<to>\d{4}-\d{2}-\d{2})\s+(?P<start>\d{2}:\d{2})-(?P<end>\d{2}:\d{2})\s+(?P<type>\w+)"
)
# Test-only syntax for exercising the "model attempted a schedule but left
# out the time" path — a real model just omits the fields, but the mock has
# no free-form understanding to omit them "naturally" from, so this is an
# explicit trigger instead.
_NO_TIME_SCHEDULE_PREFIX_RE = re.compile(r"^no-time-schedule\s*:\s*", re.IGNORECASE)
_NO_TIME_SCHEDULE_RE = re.compile(r"(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<type>\w+)")
_INCOME_PREFIX_RE = re.compile(r"^income\s*:\s*", re.IGNORECASE)
_INCOME_RE = re.compile(
    r"label=(?P<label>\S+)\s+amount=(?P<amount>[\d.]+)\s+day=(?P<day>\d+)"
    r"(?:\s+person=(?P<person>\S+))?"
)
_SUBSCRIPTION_PREFIX_RE = re.compile(r"^subscription\s*:\s*", re.IGNORECASE)
_SUBSCRIPTION_RE = re.compile(
    r"name=(?P<name>\S+)\s+amount=(?P<amount>[\d.]+)\s+kind=(?P<kind>\S+)\s+"
    r"cadence=(?P<cadence>\S+)\s+day=(?P<day>\d+)"
    r"(?:\s+month=(?P<month>\d+))?(?:\s+owner=(?P<owner>\S+))?"
)
_FINANCE_SUMMARY_RE = re.compile(r"^finance-summary\s*$", re.IGNORECASE)
# Test-only syntax for exercising the "model omitted payment_day" path —
# mirrors _NO_TIME_SCHEDULE_RE's rationale above.
_INCOME_NO_DAY_PREFIX_RE = re.compile(r"^income-no-day\s*:\s*", re.IGNORECASE)
_INCOME_NO_DAY_RE = re.compile(r"label=(?P<label>\S+)\s+amount=(?P<amount>[\d.]+)")
_SUBSCRIPTION_NO_DAY_PREFIX_RE = re.compile(r"^subscription-no-day\s*:\s*", re.IGNORECASE)
_SUBSCRIPTION_NO_DAY_RE = re.compile(
    r"name=(?P<name>\S+)\s+amount=(?P<amount>[\d.]+)\s+kind=(?P<kind>\S+)\s+"
    r"cadence=(?P<cadence>\S+)"
)


class MockLLMProvider:
    """Deterministic, network-free stand-in for a real LLM.

    Used as the default provider in dev/CI so the assistant flow (and its
    tests) never depend on a network call or an API key. It does just enough
    keyword parsing to produce the same shape of structured intent a real
    model would return — nothing about the rest of the pipeline needs to
    know it isn't talking to Gemini. Real free-form date/pattern language
    ("I work Mon-Fri 9 to 6") only needs to work against the real provider;
    the mock only has to exercise the same intent shape, hence its stricter
    "schedule: 2026-08-11 09:00-18:00 working_hours" syntax.
    """

    async def complete(self, *, system_prompt: str, user_message: str) -> str:
        text = user_message.strip()
        lowered = text.lower()
        payload: dict[str, object]

        if _FINANCE_SUMMARY_RE.match(text):
            payload = {"intent": "query_finance_summary"}
        elif _INCOME_NO_DAY_PREFIX_RE.match(text):
            rest = _INCOME_NO_DAY_PREFIX_RE.sub("", text)
            m = _INCOME_NO_DAY_RE.search(rest)
            if m:
                payload = {
                    "intent": "create_income",
                    "label": m.group("label").replace("_", " "),
                    "amount": float(m.group("amount")),
                }
            else:
                payload = {"intent": "unknown", "raw_message": text}
        elif _SUBSCRIPTION_NO_DAY_PREFIX_RE.match(text):
            rest = _SUBSCRIPTION_NO_DAY_PREFIX_RE.sub("", text)
            m = _SUBSCRIPTION_NO_DAY_RE.search(rest)
            if m:
                payload = {
                    "intent": "create_subscription",
                    "name": m.group("name").replace("_", " "),
                    "amount": float(m.group("amount")),
                    "kind": m.group("kind"),
                    "cadence": m.group("cadence"),
                }
            else:
                payload = {"intent": "unknown", "raw_message": text}
        elif _INCOME_PREFIX_RE.match(text):
            rest = _INCOME_PREFIX_RE.sub("", text)
            m = _INCOME_RE.search(rest)
            if m:
                payload = {
                    "intent": "create_income",
                    "label": m.group("label").replace("_", " "),
                    "amount": float(m.group("amount")),
                    "payment_day": int(m.group("day")),
                    "person": m.group("person"),
                }
            else:
                payload = {"intent": "unknown", "raw_message": text}
        elif _SUBSCRIPTION_PREFIX_RE.match(text):
            rest = _SUBSCRIPTION_PREFIX_RE.sub("", text)
            m = _SUBSCRIPTION_RE.search(rest)
            if m:
                month = m.group("month")
                payload = {
                    "intent": "create_subscription",
                    "name": m.group("name").replace("_", " "),
                    "amount": float(m.group("amount")),
                    "kind": m.group("kind"),
                    "cadence": m.group("cadence"),
                    "payment_day": int(m.group("day")),
                    "payment_month": int(month) if month else None,
                    "owner": m.group("owner"),
                }
            else:
                payload = {"intent": "unknown", "raw_message": text}
        elif _ROTATION_PREFIX_RE.match(text):
            rest = _ROTATION_PREFIX_RE.sub("", text)
            m = _ROTATION_RE.search(rest)
            if m:
                payload = {
                    "intent": "create_schedule",
                    "rotation": {
                        "work_days": int(m.group("work")),
                        "off_days": int(m.group("off")),
                        "date_from": m.group("from"),
                        "date_to": m.group("to"),
                        "start_time": m.group("start"),
                        "end_time": m.group("end"),
                        "event_type": m.group("type"),
                        "title": None,
                    },
                }
            else:
                payload = {"intent": "unknown", "raw_message": text}
        elif _NO_TIME_SCHEDULE_PREFIX_RE.match(text):
            rest = _NO_TIME_SCHEDULE_PREFIX_RE.sub("", text)
            m = _NO_TIME_SCHEDULE_RE.search(rest)
            if m:
                payload = {
                    "intent": "create_schedule",
                    "events": [
                        {"date": m.group("date"), "event_type": m.group("type"), "title": None}
                    ],
                }
            else:
                payload = {"intent": "unknown", "raw_message": text}
        elif _PATTERN_PREFIX_RE.match(text):
            rest = _PATTERN_PREFIX_RE.sub("", text)
            m = _PATTERN_RE.search(rest)
            if m:
                exclude = m.group("exclude")
                payload = {
                    "intent": "create_schedule",
                    "pattern": {
                        "weekdays": [int(d) for d in m.group("weekdays").split(",")],
                        "date_from": m.group("from"),
                        "date_to": m.group("to"),
                        "start_time": m.group("start"),
                        "end_time": m.group("end"),
                        "event_type": m.group("type"),
                        "title": None,
                        "exclude_dates": exclude.split(",") if exclude else [],
                    },
                }
            else:
                payload = {"intent": "unknown", "raw_message": text}
        elif _SCHEDULE_PREFIX_RE.match(text):
            rest = _SCHEDULE_PREFIX_RE.sub("", text)
            events = [
                {
                    "date": m.group("date"),
                    "start_time": m.group("start"),
                    "end_time": m.group("end"),
                    "event_type": m.group("type"),
                    "title": None,
                }
                for m in _SCHEDULE_ITEM_RE.finditer(rest)
            ]
            payload = (
                {"intent": "create_schedule", "events": events}
                if events
                else {"intent": "unknown", "raw_message": text}
            )
        elif _CREATE_TASK_PREFIX_RE.match(text):
            title = _CREATE_TASK_PREFIX_RE.sub("", text).strip()
            budget_match = _BUDGET_RE.search(title)
            budget_amount = float(budget_match.group("amount")) if budget_match else None
            budget_person = budget_match.group("person") if budget_match else None
            if budget_match:
                title = title[: budget_match.start()].strip()
            duration_match = _DURATION_RE.search(lowered)
            duration = int(duration_match.group(1)) if duration_match else None
            payload = {
                "intent": "create_task",
                "title": title or text,
                "duration_minutes": duration,
                "budget_amount": budget_amount,
                "budget_person": budget_person,
            }
        else:
            payload = {"intent": "unknown", "raw_message": text}

        return json.dumps(payload)
