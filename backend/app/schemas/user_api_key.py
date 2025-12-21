"""User API key schemas for request/response validation."""

from pydantic import BaseModel, Field


class UserApiKeyUpdate(BaseModel):
    """Request schema for updating user API key."""

    provider: str = Field(..., description="Provider name: anthropic, openai, google")
    api_key: str = Field(..., min_length=1, description="API key for the provider")


class UserApiKeysUpdate(BaseModel):
    """Request schema for updating multiple user API keys at once."""

    openai: str | None = Field(None, description="OpenAI API key")
    anthropic: str | None = Field(None, description="Anthropic API key")
    google: str | None = Field(None, description="Google API key")


class UserApiKeyResponse(BaseModel):
    """Response schema for user API key (without exposing the actual key)."""

    provider: str
    is_configured: bool
    masked_key: str | None = Field(None, description="Masked version like 'sk-...abc123'")


class UserApiKeysResponse(BaseModel):
    """Response schema for all user API keys."""

    openai: UserApiKeyResponse
    anthropic: UserApiKeyResponse
    google: UserApiKeyResponse
