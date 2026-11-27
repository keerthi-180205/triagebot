"""Application settings, loaded from environment variables and the local .env file.

Every other module gets its settings by calling get_settings(). Never read os.environ directly.
"""

from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str = "redis://localhost:6380/0"
    github_webhook_secret: SecretStr = Field(min_length=1)
    github_app_id: str = ""
    github_private_key_path: str = ""
    gemini_api_key: SecretStr = SecretStr("")
    llm_model: str = "gemini-3.8-flash"
    dry_run: bool = True
    agent_timeout_s: int = 120
    agent_max_steps: int = 10
    job_max_tries: int = 3
    runs_api_token: SecretStr = SecretStr("")

    @field_validator("github_webhook_secret")
    @classmethod
    def reject_placeholder_secret(cls, value: SecretStr) -> SecretStr:
        if value.get_secret_value() == "change-me":
            raise ValueError("github_webhook_secret is set to the placeholder value")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
