from functools import lru_cache

from home_manager.ai.cloudflare_provider import CloudflareLLMProvider
from home_manager.ai.gemini_provider import GeminiLLMProvider
from home_manager.ai.groq_provider import GroqLLMProvider
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
    (OpenAI/Anthropic/local, per the roadmap) never touches this file.
    """
    settings = get_settings()

    if settings.llm_provider == "mock":
        return MockLLMProvider()

    if settings.llm_provider == "gemini":
        if not settings.gemini_api_key:
            raise MissingLLMConfigError("GEMINI_API_KEY must be set when LLM_PROVIDER=gemini")
        return GeminiLLMProvider(api_key=settings.gemini_api_key, model=settings.llm_model)

    if settings.llm_provider == "groq":
        if not settings.groq_api_key:
            raise MissingLLMConfigError("GROQ_API_KEY must be set when LLM_PROVIDER=groq")
        return GroqLLMProvider(api_key=settings.groq_api_key, model=settings.llm_model)

    if settings.llm_provider == "cloudflare":
        if not settings.cloudflare_api_token or not settings.cloudflare_account_id:
            raise MissingLLMConfigError(
                "CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID must be set "
                "when LLM_PROVIDER=cloudflare"
            )
        return CloudflareLLMProvider(
            api_token=settings.cloudflare_api_token,
            account_id=settings.cloudflare_account_id,
            model=settings.llm_model,
        )

    raise MissingLLMConfigError(f"Unknown LLM_PROVIDER: {settings.llm_provider!r}")
