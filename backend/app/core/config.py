
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "MarketPilot AI"
    app_env: str = "development"
    app_debug: bool = True

    database_url: str
    redis_url: str

    jwt_secret: str
    auth_trusted_origin: str | None = None
    auth_idle_timeout_seconds: int = Field(default=1800, gt=0)
    auth_absolute_timeout_seconds: int = Field(default=43200, gt=0)
    openai_api_key: str = ""
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = Field(default="gemini-3.5-flash-lite", min_length=1)
    gemini_timeout_seconds: float = Field(default=90, gt=0, le=120)

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("auth_trusted_origin")
    @classmethod
    def validate_auth_origin(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            parts = urlsplit(value)
            port = parts.port
        except ValueError:
            raise ValueError("AUTH_TRUSTED_ORIGIN must be an exact HTTPS origin") from None
        if (
            parts.scheme != "https" or not parts.hostname or parts.username is not None
            or value != f"https://{parts.netloc}" or port in (0, 443)
            or not value.isascii() or any(ord(char) <= 32 or ord(char) == 127 for char in value)
            or "\\" in value or "*" in value
        ):
            raise ValueError("AUTH_TRUSTED_ORIGIN must be an exact HTTPS origin")
        return value

    @model_validator(mode="after")
    def validate_auth_timeouts(self):
        if self.auth_idle_timeout_seconds > self.auth_absolute_timeout_seconds:
            raise ValueError("Auth idle timeout must not exceed the absolute timeout")
        return self


settings = Settings()
