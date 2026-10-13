
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "GovReach AI"
    app_env: str = "development"
    app_debug: bool = True

    database_url: str
    redis_url: str

    jwt_secret: str
    openai_api_key: str = ""
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = Field(default="gemini-3.5-flash-lite", min_length=1)
    gemini_timeout_seconds: float = Field(default=90, gt=0, le=120)

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
