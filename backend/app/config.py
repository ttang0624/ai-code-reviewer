# pydantic-settings is a library that reads environment variables and validates their types.
# BaseSettings is the base class we inherit from to get that behaviour.
from pydantic_settings import BaseSettings

# We define a class that inherits from BaseSettings.
# Each attribute on the class becomes a required environment variable.
class Settings(BaseSettings):

    # SECRET_KEY is used to sign tokens or other data so we can verify it wasn't tampered with.
    SECRET_KEY: str

    # GITHUB_WEBHOOK_SECRET is the shared secret we'll use to verify payloads truly came from GitHub.
    GITHUB_WEBHOOK_SECRET: str

    # GITHUB_TOKEN is a Personal Access Token (or GitHub App token) that authenticates our outbound
    # requests to the GitHub REST API — e.g. fetching PR diffs and posting review comments.
    GITHUB_TOKEN: str

    # ANTHROPIC_API_KEY is the credential that lets us call the Claude API.
    ANTHROPIC_API_KEY: str

    # DATABASE_URL is the full connection string for PostgreSQL, e.g. postgresql://user:pass@host/db
    DATABASE_URL: str

    # The nested Config class tells pydantic-settings *where* to look for these variables.
    class Config:
        # env_file tells pydantic-settings to also read from a .env file in the working directory.
        # Variables set in the real environment always take precedence over the .env file.
        env_file = ".env"

# This creates one shared instance of Settings when the module is first imported.
# Every other file imports this `settings` object instead of reading env vars directly.
settings = Settings()
