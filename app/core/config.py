from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Distributed AI Job Orchestration Platform"
    api_prefix: str = "/api/v1"
    database_url: str = Field(
        default="postgresql+psycopg://orchestrator:orchestrator@localhost:5432/orchestrator"
    )
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "dev-secret-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    rate_limit_per_minute: int = 100
    job_create_rate_limit: str = "20/minute"
    worker_poll_interval_seconds: int = 2
    worker_heartbeat_interval_seconds: int = 10
    worker_heartbeat_ttl_seconds: int = 30
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "no-reply@example.com"
    smtp_use_tls: bool = True
    email_dry_run: bool = True
    openai_api_key: str | None = None
    groq_api_key: str | None = None
    llm_provider: str | None = None
    admin_email: str | None = None
    admin_password: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
