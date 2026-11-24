"""Application settings, loaded from environment variables or a .env file."""

from datetime import date
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Customer Return Risk Analyzer API"
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://rra_user:rra_password@localhost:5432/return_risk"
    # Stored as a comma-separated string so it reads naturally from .env.
    cors_origins: str = Field(default="http://localhost:5173")
    # Optional fixed "today" for scoring (YYYY-MM-DD). Empty = the real current date.
    scoring_as_of: date | None = None
    model_dir: str = "ml_artifacts"
    # Optional email alerts for new high-risk customers. Disabled when SMTP_HOST is empty.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    alert_email_from: str = ""
    alert_email_to: str = ""

    @field_validator("scoring_as_of", mode="before")
    @classmethod
    def _empty_date(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("cors_origins")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
