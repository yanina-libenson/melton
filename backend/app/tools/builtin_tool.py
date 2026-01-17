"""Built-in tools that execute backend functions."""

import logging
import uuid
from typing import Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models.agent import Agent
from app.models.integration import Integration
from app.models.tool import Tool
from app.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class BuiltinTool(BaseTool):
    """
    Tool that executes built-in backend functions.
    Used for meta-operations like creating agents, integrations, and tools.
    """

    def __init__(
        self,
        tool_id: str,
        config: dict[str, Any],
        session: AsyncSession,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
    ):
        super().__init__(tool_id, config)
        self.session = session  # Not used, each function gets its own session
        self.user_id = user_id
        self.organization_id = organization_id
        self.function_name = config.get("function_name")

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute the built-in function with its own database session."""
        try:
            logger.info(f"Executing builtin tool: {self.function_name} with input: {input_data}")

            # Get the function to execute
            function = BUILTIN_FUNCTIONS.get(self.function_name)
            if not function:
                return {
                    "success": False,
                    "error": f"Unknown function: {self.function_name}",
                }

            # Create a new session for this operation to avoid transaction issues
            async with async_session_maker() as new_session:
                # Execute the function with its own session
                result = await function(
                    session=new_session,
                    user_id=self.user_id,
                    organization_id=self.organization_id,
                    **input_data,
                )

            return {"success": True, "data": result}

        except Exception as e:
            logger.error(f"Builtin tool execution failed: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}

    def get_schema(self) -> dict[str, Any]:
        """Return tool schema for LLM."""
        return self.config.get("tool_schema", {})


# Built-in function implementations


async def create_agent(
    session: AsyncSession,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
    name: str,
    instructions: str,
    status: str = "draft",
    provider: str = "anthropic",
    model: str = "claude-sonnet-4-5-20250929",
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """Create a new agent."""
    agent = Agent(
        user_id=user_id,
        organization_id=organization_id,
        name=name,
        instructions=instructions,
        status=status,
        model_config={
            "provider": provider,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
    )

    session.add(agent)
    await session.flush()
    await session.refresh(agent)
    await session.commit()  # Explicit commit so agent is visible to other sessions

    return {
        "id": str(agent.id),
        "name": agent.name,
        "status": agent.status,
        "message": f"Agent '{name}' created successfully with ID: {agent.id}",
    }


async def create_integration(
    session: AsyncSession,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
    agent_id: str,
    name: str,
    description: str,
    type: str = "custom",
    platform_id: str = "custom_api",
) -> dict[str, Any]:
    """Create a new integration for an agent."""
    integration = Integration(
        agent_id=uuid.UUID(agent_id),
        type=type,
        platform_id=platform_id,
        name=name,
        description=description,
        config={},
    )

    session.add(integration)
    await session.flush()
    await session.refresh(integration)
    await session.commit()  # Explicit commit so integration is visible to other sessions

    return {
        "id": str(integration.id),
        "name": integration.name,
        "message": f"Integration '{name}' created successfully with ID: {integration.id}",
    }


async def create_api_tool(
    session: AsyncSession,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
    integration_id: str,
    name: str,
    description: str,
    endpoint: str,
    method: str = "GET",
    authentication: str = "none",
    api_key_header: str = "X-API-Key",
    api_key_value: str | None = None,
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a new API tool."""
    from app.utils.encryption import encryption_service

    # Build input schema from parameters
    input_schema = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    if parameters:
        for param_name, param_info in parameters.items():
            input_schema["properties"][param_name] = {
                "type": param_info.get("type", "string"),
                "description": param_info.get("description", ""),
            }
            if param_info.get("required", False):
                input_schema["required"].append(param_name)

    # Build tool config
    config = {
        "endpoint": endpoint,
        "method": method.upper(),
        "authentication": authentication,
        "output_mode": "full",
    }

    # Add authentication config
    if authentication == "api-key" and api_key_value:
        config["api_key_header"] = api_key_header
        config["api_key_value"] = encryption_service.encrypt(api_key_value)

    tool = Tool(
        integration_id=uuid.UUID(integration_id),
        name=name,
        description=description,
        tool_type="api",
        tool_schema={
            "name": name,
            "description": description,
            "input_schema": input_schema,
        },
        config=config,
        is_enabled=True,
    )

    session.add(tool)
    await session.flush()
    await session.refresh(tool)
    await session.commit()  # Explicit commit so tool is visible to other sessions

    return {
        "id": str(tool.id),
        "name": tool.name,
        "message": f"API tool '{name}' created successfully with ID: {tool.id}",
    }


# Registry of available builtin functions
BUILTIN_FUNCTIONS: dict[str, Callable] = {
    "create_agent": create_agent,
    "create_integration": create_integration,
    "create_api_tool": create_api_tool,
}
