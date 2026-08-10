import httpx

from home_manager.ai.provider import LLMProviderError

GROQ_API_BASE = "https://api.groq.com/openai/v1"


class GroqLLMProvider:
    """Talks to Groq's OpenAI-compatible chat completions endpoint.

    Same minimal-footprint approach as GeminiLLMProvider — a handful of
    fields over httpx, no SDK dependency.
    """

    def __init__(self, *, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    async def complete(self, *, system_prompt: str, user_message: str) -> str:
        url = f"{GROQ_API_BASE}/chat/completions"
        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.post(url, headers=headers, json=body)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise LLMProviderError() from exc

        data = response.json()
        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError() from exc
