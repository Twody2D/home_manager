import json
import re

_DURATION_RE = re.compile(r"(\d+)\s*(?:min|minutes?|мин\w*)")
_CREATE_TASK_PREFIX_RE = re.compile(
    r"^(create task|add task|remind me to|new task)\s*:?\s*", re.IGNORECASE
)
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

        if _ROTATION_PREFIX_RE.match(text):
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
            duration_match = _DURATION_RE.search(lowered)
            duration = int(duration_match.group(1)) if duration_match else None
            payload = {
                "intent": "create_task",
                "title": title or text,
                "duration_minutes": duration,
            }
        else:
            payload = {"intent": "unknown", "raw_message": text}

        return json.dumps(payload)
