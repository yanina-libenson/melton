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

    # OAuth
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"
    oauth_state_expiry_seconds: int = 600  # 10 minutes
    mercadolibre_client_id: str | None = None
    mercadolibre_client_secret: str | None = None

    # Environment
    environment: str = "development"
    debug: bool = True

    # CORS
    cors_origins: str | None = None

    def get_cors_origins(self) -> list[str]:
        """Parse CORS origins from comma-separated string or return defaults."""
        if self.cors_origins:
            return [origin.strip() for origin in self.cors_origins.split(",")]
        return ["http://localhost:3000", "http://localhost:3001"]

    # API
    api_v1_prefix: str = "/api/v1"

    # Tool execution
    tool_execution_timeout: int = 30  # seconds
    max_tool_retries: int = 3

    # Subdomain deployment
    subdomain_enabled: bool = True
    base_domain: str = "melton.com"


settings = Settings()
