"""Unit tests for ToolRegistry."""

from typing import Any

import pytest

from app.tools.base_tool import BaseTool
from app.tools.registry import ToolRegistry


class MockTool(BaseTool):
    """Mock tool for testing."""

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return {"result": "success", "input": input_data}

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Query parameter"}
                },
                "required": ["query"],
            },
        }


def test_registry_singleton():
    """Test that ToolRegistry is a singleton."""
    registry1 = ToolRegistry()
    registry2 = ToolRegistry()

    assert registry1 is registry2


def test_register_and_get_tool():
    """Test registering and retrieving a tool."""
    registry = ToolRegistry()
    registry.clear()  # Clear for isolated test

    tool = MockTool("test-tool", {"name": "Test Tool", "description": "A test tool"})
    registry.register(tool)

    retrieved_tool = registry.get("test-tool")
    assert retrieved_tool is not None
    assert retrieved_tool.tool_id == "test-tool"
    assert retrieved_tool.name == "Test Tool"


def test_unregister_tool():
    """Test unregistering a tool."""
    registry = ToolRegistry()
    registry.clear()

    tool = MockTool("test-tool", {"name": "Test Tool", "description": "A test tool"})
    registry.register(tool)

    registry.unregister("test-tool")

    retrieved_tool = registry.get("test-tool")
    assert retrieved_tool is None


def test_list_tools():
    """Test listing registered tools."""
    registry = ToolRegistry()
    registry.clear()

    tool1 = MockTool("tool-1", {"name": "Tool 1", "description": "First tool"})
    tool2 = MockTool("tool-2", {"name": "Tool 2", "description": "Second tool"})

    registry.register(tool1)
    registry.register(tool2)

    tool_ids = registry.list_tools()

    assert len(tool_ids) == 2
    assert "tool-1" in tool_ids
    assert "tool-2" in tool_ids


def test_get_schemas_for_agent():
    """Test getting tool schemas for an agent."""
    registry = ToolRegistry()
    registry.clear()

    tool1 = MockTool("tool-1", {"name": "Tool 1", "description": "First tool"})
    tool2 = MockTool("tool-2", {"name": "Tool 2", "description": "Second tool"})

    registry.register(tool1)
    registry.register(tool2)

    schemas = registry.get_schemas_for_agent("agent-1", ["tool-1", "tool-2"])

    assert len(schemas) == 2
    assert all("name" in schema for schema in schemas)
    assert all("description" in schema for schema in schemas)
    assert all("input_schema" in schema for schema in schemas)


@pytest.mark.asyncio
async def test_mock_tool_execution():
    """Test executing a mock tool."""
    tool = MockTool("test-tool", {"name": "Test Tool", "description": "A test tool"})

    result = await tool.execute({"query": "test query"})

    assert result["result"] == "success"
    assert result["input"]["query"] == "test query"
