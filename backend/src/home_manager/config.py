from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"

    database_url: str = "postgresql+asyncpg://home_manager:home_manager@localhost:5432/home_manager"

    jwt_secret: str = "change-me-in-env"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    cors_allowed_origins: list[str] = ["http://localhost:5173"]

    llm_provider: str = "mock"
    llm_model: str = "gemini-2.0-flash"
    gemini_api_key: str | None = None

    # Web push is disabled (subscribe/send become no-ops) unless both keys
    # are set. Generate a pair with: uv run python scripts/generate_vapid_keys.py
    vapid_public_key: str | None = None
    vapid_private_key: str | None = None
    vapid_subject: str = "mailto:admin@example.com"

    smart_home_provider: str = "mock"
    home_assistant_url: str | None = None
    home_assistant_token: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
