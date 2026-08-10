from functools import lru_cache

from home_manager.ai.gemini_provider import GeminiLLMProvider
from home_manager.ai.mock_provider import MockLLMProvider
from home_manager.ai.provider import LLMProvider
from home_manager.config import get_settings


class MissingLLMConfigError(RuntimeError):
    pass


@lru_cache
def get_llm_provider() -> LLMProvider:
    """Builds the configured provider once per process.

    Which backend is used — and which model — comes entirely from env
    (LLM_PROVIDER, LLM_MODEL), never hardcoded, so swapping providers
    (Groq/OpenAI/Anthropic/local, per the roadmap) never touches this file.
    """
    settings = get_settings()

    if settings.llm_provider == "mock":
        return MockLLMProvider()

    if settings.llm_provider == "gemini":
        if not settings.gemini_api_key:
            raise MissingLLMConfigError("GEMINI_API_KEY must be set when LLM_PROVIDER=gemini")
        return GeminiLLMProvider(api_key=settings.gemini_api_key, model=settings.llm_model)

    raise MissingLLMConfigError(f"Unknown LLM_PROVIDER: {settings.llm_provider!r}")
