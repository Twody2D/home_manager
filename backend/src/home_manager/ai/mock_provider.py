import json
import re

_DURATION_RE = re.compile(r"(\d+)\s*(?:min|minutes?|мин\w*)")
_CREATE_TASK_PREFIX_RE = re.compile(
    r"^(create task|add task|remind me to|new task)\s*:?\s*", re.IGNORECASE
)


class MockLLMProvider:
    """Deterministic, network-free stand-in for a real LLM.

    Used as the default provider in dev/CI so the assistant flow (and its
    tests) never depend on a network call or an API key. It does just enough
    keyword parsing to produce the same shape of structured intent a real
    model would return — nothing about the rest of the pipeline needs to
    know it isn't talking to Gemini.
    """

    async def complete(self, *, system_prompt: str, user_message: str) -> str:
        text = user_message.strip()
        lowered = text.lower()

        if _CREATE_TASK_PREFIX_RE.match(text):
            title = _CREATE_TASK_PREFIX_RE.sub("", text).strip()
            duration_match = _DURATION_RE.search(lowered)
            duration = int(duration_match.group(1)) if duration_match else None
            payload: dict[str, object] = {
                "intent": "create_task",
                "title": title or text,
                "duration_minutes": duration,
            }
        else:
            payload = {"intent": "unknown", "raw_message": text}

        return json.dumps(payload)
