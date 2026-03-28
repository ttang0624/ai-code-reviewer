# Loads environment variables and exposes them as typed settings.
# All secrets and configuration values should be read from here — never hardcoded elsewhere.

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    github_webhook_secret: str
    github_token: str
    anthropic_api_key: str
    database_url: str

    class Config:
        env_file = ".env"

settings = Settings()
