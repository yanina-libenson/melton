"""Tool registry singleton for managing tool instances."""

from typing import Any

from app.tools.base_tool import BaseTool


class ToolRegistry:
    """
    Singleton registry for all tools.
    Manages tool lifecycle and provides access to tool instances.
    """

    _instance: "ToolRegistry | None" = None
    _tools: dict[str, BaseTool] = {}

    def __new__(cls) -> "ToolRegistry":
        """Ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
        return cls._instance

    def register(self, tool: BaseTool) -> None:
        """
        Register a tool instance.

        Args:
            tool: Tool instance to register
        """
        self._tools[tool.tool_id] = tool

    def unregister(self, tool_id: str) -> None:
        """
        Unregister a tool.

        Args:
            tool_id: Tool ID to unregister
        """
        if tool_id in self._tools:
            del self._tools[tool_id]

    def get(self, tool_id: str) -> BaseTool | None:
        """
        Get a tool by ID.

        Args:
            tool_id: Tool ID

        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(tool_id)

    def get_schemas_for_agent(self, agent_id: str, tool_ids: list[str]) -> list[dict[str, Any]]:
        """
        Get tool schemas for an agent.

        Args:
            agent_id: Agent ID
            tool_ids: List of tool IDs to get schemas for

        Returns:
            List of tool schemas in standard format
        """
        schemas = []
        for tool_id in tool_ids:
            tool = self.get(tool_id)
            if tool:
                schemas.append(tool.get_schema())
        return schemas

    def list_tools(self) -> list[str]:
        """List all registered tool IDs."""
        return list(self._tools.keys())

    def clear(self) -> None:
        """Clear all registered tools (useful for testing)."""
        self._tools.clear()
