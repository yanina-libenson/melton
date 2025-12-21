"""Agent Pydantic schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    """Model configuration schema."""

    provider: Literal["anthropic", "openai", "google"] = Field(..., description="LLM provider")
    model: str = Field(..., description="Model identifier", examples=["claude-sonnet-4-20250514"])
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperature for generation")
    max_tokens: int = Field(default=4096, gt=0, le=100000, description="Maximum tokens to generate")
    top_p: float | None = Field(default=None, ge=0.0, le=1.0, description="Top-p sampling")


class AgentCreate(BaseModel):
    """Schema for creating a new agent."""

    name: str = Field(..., min_length=1, max_length=255, description="Agent name")
    instructions: str = Field(..., min_length=20, description="System instructions for the agent")
    status: Literal["active", "inactive", "draft"] = Field(default="draft", description="Agent status")
    llm_config: ModelConfig = Field(..., description="LLM model configuration", alias="model_config")

    model_config = {"populate_by_name": True, "json_schema_extra": {"examples": [{
        "name": "Customer Support Agent",
        "instructions": "You are a helpful customer support agent...",
        "status": "draft",
        "model_config": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-20250514",
            "temperature": 0.7,
            "max_tokens": 4096
        }
    }]}}


class AgentUpdate(BaseModel):
    """Schema for updating an agent."""

    name: str | None = Field(None, min_length=1, max_length=255)
    instructions: str | None = Field(None, min_length=20)
    status: Literal["active", "inactive", "draft"] | None = None
    llm_config: ModelConfig | None = Field(None, alias="model_config")

    model_config = {"populate_by_name": True}


class AgentResponse(BaseModel):
    """Schema for agent response."""

    id: UUID
    user_id: UUID
    organization_id: UUID
    name: str
    instructions: str
    status: Literal["active", "inactive", "draft"]
    llm_config: dict = Field(..., alias="model_config")
    created_at: datetime
    updated_at: datetime
    integrations: list["IntegrationResponse"] = []

    model_config = {"from_attributes": True, "populate_by_name": True}


# Import here to avoid circular dependency
from app.schemas.integration import IntegrationResponse  # noqa: E402

AgentResponse.model_rebuild()
