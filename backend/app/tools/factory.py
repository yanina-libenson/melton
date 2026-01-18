"""Tool factory for creating tool instances from database records."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tool import Tool as ToolModel
from app.tools.api_tool import APITool
from app.tools.base_tool import BaseTool
from app.tools.builtin_tool import BuiltinTool
from app.tools.llm_tool import LLMTool


class ToolFactory:
    """
    Factory for creating tool instances from database records.
    Handles instantiation of APITool, LLMTool, BuiltinTool, and future tool types.
    """

    @staticmethod
    def create_tool(
        tool_model: ToolModel,
        api_key: str | None = None,
        session: AsyncSession | None = None,
        user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> BaseTool:
        """
        Create a tool instance from a database model.

        Args:
            tool_model: Tool database model
            api_key: API key for LLM tools
            session: Database session (required for builtin tools)
            user_id: User ID (required for builtin tools)
            organization_id: Organization ID (required for builtin tools)

        Returns:
            BaseTool instance (APITool, LLMTool, BuiltinTool, or Platform Tool)

        Raises:
            ValueError: If tool type is unsupported
        """
        tool_type = tool_model.tool_type

        # Handle builtin tools first (before checking platform_id)
        if tool_type == "builtin":
            if not session or not user_id or not organization_id:
                raise ValueError("Builtin tools require session, user_id, and organization_id")
            return ToolFactory._create_builtin_tool(tool_model, session, user_id, organization_id)

        # Check if this is a real platform integration (pre-built)
        # Only treat as platform if integration.type is "platform"
        if tool_model.integration.type == "platform" and tool_model.integration.platform_id:
            return ToolFactory._create_platform_tool(tool_model)

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

    @staticmethod
    def _create_platform_tool(tool_model: ToolModel) -> BaseTool:
        """
        Create a pre-built platform tool instance.

        Args:
            tool_model: Tool database model with integration.platform_id

        Returns:
            Platform-specific tool instance

        Raises:
            ValueError: If platform not supported
        """
        platform_id = tool_model.integration.platform_id
        tool_name = tool_model.name.lower()

        # Mercado Libre platform
        if platform_id == "mercadolibre":
            from app.tools.platforms.mercadolibre import (
                MercadoLibreCategoriesTool,
                MercadoLibrePublicationsTool,
                MercadoLibreQuestionsTool,
                MercadoLibreSearchTool,
                MercadoLibreSizeGridsTool,
            )

            # Determine which tool based on tool name or config
            if "publication" in tool_name or tool_name == "ml-publications":
                return MercadoLibrePublicationsTool(
                    tool_id=str(tool_model.id),
                    tool_config=tool_model.config,
                    integration=tool_model.integration,
                )
            elif "question" in tool_name or tool_name == "ml-questions":
                return MercadoLibreQuestionsTool(
                    tool_id=str(tool_model.id),
                    tool_config=tool_model.config,
                    integration=tool_model.integration,
                )
            elif "categor" in tool_name or tool_name == "ml-categories":
                return MercadoLibreCategoriesTool(
                    tool_id=str(tool_model.id),
                    tool_config=tool_model.config,
                    integration=tool_model.integration,
                )
            elif "search" in tool_name or tool_name == "ml-search":
                return MercadoLibreSearchTool(
                    tool_id=str(tool_model.id),
                    tool_config=tool_model.config,
                    integration=tool_model.integration,
                )
            elif "sizegrid" in tool_name or "size" in tool_name and "grid" in tool_name or tool_name == "ml-sizegrids":
                return MercadoLibreSizeGridsTool(
                    tool_id=str(tool_model.id),
                    tool_config=tool_model.config,
                    integration=tool_model.integration,
                )
            else:
                raise ValueError(f"Unknown Mercado Libre tool: {tool_name}")

        # Add more platforms here as they are implemented
        else:
            raise ValueError(f"Platform {platform_id} not supported")

    @staticmethod
    def _create_builtin_tool(
        tool_model: ToolModel,
        session: AsyncSession,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> BuiltinTool:
        """Create a BuiltinTool instance."""
        config = {
            "name": tool_model.name,
            "description": tool_model.description,
            "function_name": tool_model.config.get("function_name"),
            "tool_schema": tool_model.tool_schema,
            **tool_model.config,
        }

        return BuiltinTool(
            tool_id=str(tool_model.id),
            config=config,
            session=session,
            user_id=user_id,
            organization_id=organization_id,
        )
