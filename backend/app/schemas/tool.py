"""Tool Pydantic schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ToolSchema(BaseModel):
    """Tool schema definition for LLM."""

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    input_schema: dict = Field(..., description="JSON Schema for input parameters")


class ToolCreate(BaseModel):
    """Schema for creating a new tool."""

    integration_id: UUID = Field(..., description="Integration ID this tool belongs to")
    name: str = Field(..., min_length=1, max_length=255, description="Tool name")
    description: str | None = Field(None, description="Tool description")
    tool_type: Literal["api", "llm", "sub-agent", "builtin"] | None = Field(None, description="Tool type")
    tool_schema: dict = Field(default_factory=dict, description="Tool schema for LLM")
    config: dict = Field(default_factory=dict, description="Tool configuration")
    is_enabled: bool = Field(default=True, description="Whether the tool is enabled")

    model_config = {"json_schema_extra": {"examples": [{
        "integration_id": "550e8400-e29b-41d4-a716-446655440001",
        "name": "Get Customer",
        "description": "Retrieve customer information by ID",
        "tool_type": "api",
        "tool_schema": {
            "name": "get_customer",
            "description": "Retrieve customer information",
            "input_schema": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "Customer ID"
                    }
                },
                "required": ["customer_id"]
            }
        },
        "config": {
            "endpoint": "/customers/{customer_id}",
            "method": "GET"
        },
        "is_enabled": True
    }]}}


class ToolUpdate(BaseModel):
    """Schema for updating a tool."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    tool_schema: dict | None = None
    config: dict | None = None
    is_enabled: bool | None = None


class ToolResponse(BaseModel):
    """Schema for tool response."""

    id: UUID
    integration_id: UUID = Field(..., serialization_alias="sourceId")
    name: str
    description: str | None
    tool_type: Literal["api", "llm", "sub-agent", "builtin"] | None = Field(None, serialization_alias="toolType")
    tool_schema: dict = Field(..., serialization_alias="toolSchema")
    config: dict
    is_enabled: bool = Field(..., serialization_alias="isEnabled")
    created_at: datetime = Field(..., serialization_alias="createdAt")
    updated_at: datetime = Field(..., serialization_alias="updatedAt")

    model_config = {"from_attributes": True, "populate_by_name": True}


class ToolTestRequest(BaseModel):
    """Schema for testing a tool configuration."""

    # API configuration
    endpoint: str = Field(..., description="API endpoint URL (supports {variable} templating)")
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = Field(
        default="GET", description="HTTP method"
    )
    authentication: Literal["none", "api-key", "bearer", "basic"] = Field(
        default="none", description="Authentication type"
    )
    auth_config: dict = Field(default_factory=dict, description="Authentication configuration")

    # Tool input/output configuration
    test_input: dict = Field(default_factory=dict, description="Test input values")
    output_mode: Literal["full", "extract", "llm"] = Field(
        default="full", description="Output transformation mode"
    )
    output_mapping: dict = Field(
        default_factory=dict, description="Field extraction mapping (for extract mode)"
    )
    llm_config: dict | None = Field(None, description="LLM transformation config (for llm mode)")


class ToolTestResponse(BaseModel):
    """Schema for tool test result."""

    success: bool
    output: dict | list | str | None
    error: str | None = None
    debug_info: dict | None = Field(
        None, description="Debug information (API response, execution time, etc.)"
    )
