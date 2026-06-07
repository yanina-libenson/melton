"""Unit tests for ToolRegistry.

ToolRegistry is per-execution (NOT a singleton): a fresh registry is created
for each conversation so credentialed tool instances never leak across
concurrent conversations or users.
"""

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


def test_registry_instances_are_isolated():
    """Two registries must be independent instances with independent state.

    This is the security property that replaced the old singleton: one user's
    conversation must never see another conversation's registered tools.
    """
    registry1 = ToolRegistry()
    registry2 = ToolRegistry()

    assert registry1 is not registry2

    tool = MockTool("secret-tool", {"name": "secret-tool", "description": "A's tool"})
    registry1.register("secret-tool", tool)

    # The tool registered in registry1 must NOT be visible in registry2.
    assert registry1.get("secret-tool") is tool
    assert registry2.get("secret-tool") is None
    assert registry2.list_tools() == []


def test_register_and_get_tool():
    """Test registering and retrieving a tool."""
    registry = ToolRegistry()

    tool = MockTool("test-tool", {"name": "test-tool", "description": "A test tool"})
    registry.register("test-tool", tool)

    retrieved_tool = registry.get("test-tool")
    assert retrieved_tool is not None
    assert retrieved_tool.tool_id == "test-tool"
    assert retrieved_tool.name == "test-tool"


def test_unregister_tool():
    """Test unregistering a tool."""
    registry = ToolRegistry()

    tool = MockTool("test-tool", {"name": "test-tool", "description": "A test tool"})
    registry.register("test-tool", tool)

    registry.unregister("test-tool")

    assert registry.get("test-tool") is None


def test_list_tools():
    """Test listing registered tools."""
    registry = ToolRegistry()

    tool1 = MockTool("tool-1", {"name": "tool-1", "description": "First tool"})
    tool2 = MockTool("tool-2", {"name": "tool-2", "description": "Second tool"})

    registry.register("tool-1", tool1)
    registry.register("tool-2", tool2)

    tool_ids = registry.list_tools()

    assert len(tool_ids) == 2
    assert set(tool_ids) == {"tool-1", "tool-2"}


def test_get_schemas_for_agent():
    """Test getting tool schemas for an agent."""
    registry = ToolRegistry()

    tool1 = MockTool("tool-1", {"name": "tool-1", "description": "First tool"})
    tool2 = MockTool("tool-2", {"name": "tool-2", "description": "Second tool"})

    registry.register("tool-1", tool1)
    registry.register("tool-2", tool2)

    schemas = registry.get_schemas_for_agent("agent-1", ["tool-1", "tool-2"])

    assert len(schemas) == 2
    assert all("name" in schema for schema in schemas)
    assert all("description" in schema for schema in schemas)
    assert all("input_schema" in schema for schema in schemas)


@pytest.mark.asyncio
async def test_mock_tool_execution():
    """Test executing a mock tool."""
    tool = MockTool("test-tool", {"name": "test-tool", "description": "A test tool"})

    result = await tool.execute({"query": "test query"})

    assert result["result"] == "success"
    assert result["input"]["query"] == "test query"
