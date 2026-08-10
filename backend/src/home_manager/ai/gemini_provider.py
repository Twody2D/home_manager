import httpx

from home_manager.ai.provider import LLMProviderError

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiLLMProvider:
    """Talks to the Gemini API directly over HTTPS.

    Deliberately no google-genai SDK dependency — this is a handful of
    fields over httpx (already a project dependency), which keeps the
    footprint small and the request/response shape fully visible here.
    """

    def __init__(self, *, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    async def complete(self, *, system_prompt: str, user_message: str) -> str:
        url = f"{GEMINI_API_BASE}/models/{self._model}:generateContent"
        body = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_message}]}],
            "generationConfig": {"response_mime_type": "application/json"},
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.post(url, params={"key": self._api_key}, json=body)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise LLMProviderError() from exc

        data = response.json()
        try:
            return str(data["candidates"][0]["content"]["parts"][0]["text"])
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError() from exc
