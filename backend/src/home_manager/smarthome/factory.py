from functools import lru_cache

from home_manager.config import get_settings
from home_manager.smarthome.home_assistant_provider import HomeAssistantProvider
from home_manager.smarthome.mock_provider import MockSmartHomeProvider
from home_manager.smarthome.provider import SmartHomeProvider


class MissingSmartHomeConfigError(RuntimeError):
    pass


@lru_cache
def get_smart_home_provider() -> SmartHomeProvider:
    """Builds the configured provider once per process.

    Which hub is used comes entirely from env (SMART_HOME_PROVIDER,
    HOME_ASSISTANT_URL, HOME_ASSISTANT_TOKEN), never hardcoded — a future
    Yandex Smart Home adapter plugs in here the same way GeminiProvider did
    for LLM_PROVIDER.
    """
    settings = get_settings()

    if settings.smart_home_provider == "mock":
        return MockSmartHomeProvider()

    if settings.smart_home_provider == "home_assistant":
        if not settings.home_assistant_url or not settings.home_assistant_token:
            raise MissingSmartHomeConfigError(
                "HOME_ASSISTANT_URL and HOME_ASSISTANT_TOKEN must be set when "
                "SMART_HOME_PROVIDER=home_assistant"
            )
        return HomeAssistantProvider(
            base_url=settings.home_assistant_url, token=settings.home_assistant_token
        )

    raise MissingSmartHomeConfigError(
        f"Unknown SMART_HOME_PROVIDER: {settings.smart_home_provider!r}"
    )
