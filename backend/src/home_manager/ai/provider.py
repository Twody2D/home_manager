from typing import Protocol

from fastapi import status

from home_manager.core.errors import AppError


class LLMProviderError(AppError):
    code = "LLM_PROVIDER_ERROR"
    status_code = status.HTTP_502_BAD_GATEWAY
    message = "The AI provider failed to respond"


class LLMProvider(Protocol):
    """Abstraction over a text-completion backend.

    Implementations are pure request/response — no direct DB access, no
    Home Assistant access, no side effects of any kind. Whatever a provider
    returns is untrusted input: callers must run it through Pydantic
    validation, then business validation, then authorization, before acting
    on it (see home_manager.assistant.service).
    """

    async def complete(self, *, system_prompt: str, user_message: str) -> str: ...
