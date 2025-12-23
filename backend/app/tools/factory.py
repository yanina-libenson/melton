"""Tool factory for creating tool instances from database records."""


from app.models.tool import Tool as ToolModel
from app.tools.api_tool import APITool
from app.tools.base_tool import BaseTool
from app.tools.llm_tool import LLMTool


class ToolFactory:
    """
    Factory for creating tool instances from database records.
    Handles instantiation of APITool, LLMTool, and future tool types.
    """

    @staticmethod
    def create_tool(tool_model: ToolModel, api_key: str | None = None) -> BaseTool:
        """
        Create a tool instance from a database model.

        Args:
            tool_model: Tool database model
            api_key: API key for LLM tools

        Returns:
            BaseTool instance (APITool or LLMTool)

        Raises:
            ValueError: If tool type is unsupported
        """
        tool_type = tool_model.tool_type

        if tool_type == "api":
            return ToolFactory._create_api_tool(tool_model)
        elif tool_type == "llm":
            return ToolFactory._create_llm_tool(tool_model, api_key)
        elif tool_type == "sub-agent":
            # Phase 4 - not implemented yet
            raise ValueError("Sub-agent tools not yet supported")
        else:
            raise ValueError(f"Unknown tool type: {tool_type}")

    @staticmethod
    def _create_api_tool(tool_model: ToolModel) -> APITool:
        """Create an APITool instance."""
        # Get integration config for base URL and authentication
        integration_config = tool_model.integration.config or {}

        config = {
            "name": tool_model.name,
            "description": tool_model.description,
            # Get endpoint from integration's baseUrl
            "endpoint": integration_config.get("baseUrl", ""),
            "method": integration_config.get("method", "GET"),
            "authentication": integration_config.get("authentication", "none"),
            "timeout": integration_config.get("timeout", 30),
            # LLM enhancement from tool config
            "llm_enhanced": tool_model.config.get("llm_enabled", False),
            "llm_model": tool_model.config.get("llm_model"),
            "llm_instructions": tool_model.config.get("llm_instructions"),
            # Include input_schema from tool_schema for validation
            "input_schema": tool_model.tool_schema.get("input_schema", {}),
            # Merge auth config from integration
            **integration_config,
            # Override with tool-specific config
            **tool_model.config,
        }

        return APITool(tool_id=str(tool_model.id), config=config)

    @staticmethod
    def _create_llm_tool(tool_model: ToolModel, api_key: str | None) -> LLMTool:
        """Create an LLMTool instance."""
        return LLMTool(
            tool_id=str(tool_model.id),
            name=tool_model.name,
            description=tool_model.description or "",
            tool_schema=tool_model.tool_schema,
            config=tool_model.config,
            api_key=api_key,
        )
