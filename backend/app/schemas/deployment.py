"""Deployment Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DeploymentResponse(BaseModel):
    """Schema for a channel deployment."""

    id: UUID
    agent_id: UUID = Field(..., serialization_alias="agentId")
    channel_type: str = Field(..., serialization_alias="channelType")
    is_active: bool = Field(..., serialization_alias="isActive")
    config: dict = Field(default={})
    created_at: datetime = Field(..., serialization_alias="createdAt")
    updated_at: datetime = Field(..., serialization_alias="updatedAt")

    model_config = {"from_attributes": True, "populate_by_name": True}


class DeploymentCreate(BaseModel):
    """Optional per-channel config when deploying."""

    config: dict = Field(default={})
