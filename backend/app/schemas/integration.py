"""Integration Pydantic schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class IntegrationConfig(BaseModel):
    """Integration configuration schema."""

    endpoint: str | None = None
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] | None = None
    authentication: Literal["none", "api-key", "bearer", "basic", "oauth", "custom"] | None = None
    # Additional config stored as dict
    extra: dict = Field(default_factory=dict)


class IntegrationCreate(BaseModel):
    """Schema for creating a new integration."""

    agent_id: UUID = Field(..., description="Agent ID this integration belongs to")
    type: Literal["platform", "custom-tool", "sub-agent"] = Field(..., description="Integration type")
    platform_id: str | None = Field(None, description="Platform identifier (for platform integrations)")
    name: str = Field(..., min_length=1, max_length=255, description="Integration name")
    description: str | None = Field(None, description="Integration description")
    config: dict = Field(default_factory=dict, description="Integration configuration")

    model_config = {"json_schema_extra": {"examples": [{
        "agent_id": "550e8400-e29b-41d4-a716-446655440000",
        "type": "custom-tool",
        "name": "Custom API Tool",
        "description": "Integration with external API",
        "config": {
            "endpoint": "https://api.example.com",
            "method": "POST",
            "authentication": "bearer"
        }
    }]}}


class IntegrationUpdate(BaseModel):
    """Schema for updating an integration."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    config: dict | None = None


class IntegrationResponse(BaseModel):
    """Schema for integration response."""

    id: UUID
    agent_id: UUID = Field(..., serialization_alias="agentId")
    type: Literal["platform", "custom-tool", "sub-agent"]
    platform_id: str | None = Field(None, serialization_alias="platformId")
    name: str
    description: str | None
    config: dict
    created_at: datetime = Field(..., serialization_alias="createdAt")
    updated_at: datetime = Field(..., serialization_alias="updatedAt")
    tools: list["ToolResponse"] = Field(default=[], serialization_alias="availableTools")

    model_config = {"from_attributes": True, "populate_by_name": True}


# Import here to avoid circular dependency
from app.schemas.tool import ToolResponse  # noqa: E402

IntegrationResponse.model_rebuild()
