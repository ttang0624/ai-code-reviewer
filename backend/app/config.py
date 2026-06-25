from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or backend/.env."""

    app_name: str = "AI Code Reviewer"
    environment: str = "development"
    secret_key: str = "dev-only-change-me"

    github_webhook_secret: str = "dev-webhook-secret"
    github_token: str | None = None

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-haiku-4-5-20251001"
    max_diff_chars: int = Field(default=60_000, ge=1_000, le=200_000)

    database_url: str = "sqlite:///./ai_code_reviewer.db"
    dry_run_without_ai: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
