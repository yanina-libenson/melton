"""Base tool abstract class."""

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """
    Abstract base class for all tools.
    Keep implementations under 200 lines and focused.
    """

    def __init__(self, tool_id: str, config: dict[str, Any]):
        self.tool_id = tool_id
        self.config = config
        self.name = config.get("name", tool_id)
        self.description = config.get("description", "")

    @abstractmethod
    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the tool with given input.

        Args:
            input_data: Tool input parameters

        Returns:
            Tool execution result

        Raises:
            Exception: If tool execution fails
        """
        pass

    @abstractmethod
    def get_schema(self) -> dict[str, Any]:
        """
        Return tool schema for LLM.

        Returns:
            Tool schema in standard format:
            {
                "name": str,
                "description": str,
                "input_schema": dict (JSON Schema)
            }
        """
        pass

    def validate_input(self, input_data: dict[str, Any]) -> bool:
        """
        Validate input parameters against schema.

        Args:
            input_data: Input parameters to validate

        Returns:
            True if valid, False otherwise
        """
        # Basic validation - can be enhanced with jsonschema
        schema = self.get_schema()
        input_schema = schema.get("input_schema", {})
        required = input_schema.get("required", [])

        # Check required fields
        return all(field in input_data for field in required)
