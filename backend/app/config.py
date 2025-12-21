"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://melton:melton_dev_password@localhost:5432/melton"
    database_url_sync: str = "postgresql://melton:melton_dev_password@localhost:5432/melton"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    secret_key: str = "development-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15

    # LLM API Keys (optional - users can provide their own)
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    google_api_key: str | None = None

    # LangFuse
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"

    # Encryption
    encryption_key: str = "development-encryption-key-change-in-production"

    # Environment
    environment: str = "development"
    debug: bool = True

    # API
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    # Tool execution
    tool_execution_timeout: int = 30  # seconds
    max_tool_retries: int = 3


settings = Settings()
