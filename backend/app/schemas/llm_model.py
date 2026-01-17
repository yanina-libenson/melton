"""LLM Model Pydantic schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class LLMModelResponse(BaseModel):
    """Schema for LLM model response."""

    id: UUID
    model_id: str = Field(..., serialization_alias="modelId")
    provider: Literal["anthropic", "openai", "google"]
    display_name: str = Field(..., serialization_alias="displayName")
    is_active: bool = Field(..., serialization_alias="isActive")
    created_at: datetime = Field(..., serialization_alias="createdAt")
    updated_at: datetime = Field(..., serialization_alias="updatedAt")

    model_config = {"from_attributes": True, "populate_by_name": True}
