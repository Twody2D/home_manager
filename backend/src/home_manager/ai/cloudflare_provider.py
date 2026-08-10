import json

import httpx

from home_manager.ai.provider import LLMProviderError

CLOUDFLARE_API_BASE = "https://api.cloudflare.com/client/v4/accounts"


class CloudflareLLMProvider:
    """Talks to Cloudflare Workers AI's OpenAI-style chat endpoint.

    Same minimal-footprint approach as the other providers — a handful of
    fields over httpx, no SDK dependency.
    """

    def __init__(self, *, api_token: str, account_id: str, model: str) -> None:
        self._api_token = api_token
        self._account_id = account_id
        self._model = model

    async def complete(self, *, system_prompt: str, user_message: str) -> str:
        url = f"{CLOUDFLARE_API_BASE}/{self._account_id}/ai/run/{self._model}"
        body = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            # A full month of shifts (up to the calendar bulk-create limit of
            # 60 events) easily runs past the API's low default completion
            # length, truncating the JSON mid-object — seen in testing as a
            # response cut off at the default 256 tokens.
            "max_tokens": 4096,
        }
        headers = {"Authorization": f"Bearer {self._api_token}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, headers=headers, json=body)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise LLMProviderError() from exc

        data = response.json()
        if data.get("success") is not True:
            raise LLMProviderError()
        try:
            content = data["result"]["response"]
        except (KeyError, TypeError) as exc:
            raise LLMProviderError() from exc

        # Workers AI sometimes auto-parses a JSON-looking reply into an
        # object instead of returning it as a string — re-serialize so the
        # caller always gets text to run through its own json.loads.
        return content if isinstance(content, str) else json.dumps(content)
