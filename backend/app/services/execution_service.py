"""Agent execution service - orchestrates conversation flow with streaming."""

import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.factory import LLMProviderFactory
from app.models.agent import Agent
from app.services.conversation_service import ConversationService
from app.services.llm_model_service import LLMModelService
from app.tools.registry import ToolRegistry
from app.utils.observability import observability_service, trace_execution


class ExecutionEvent:
    """Streaming event for WebSocket communication."""

    def __init__(self, event_type: str, **data: Any):
        self.type = event_type
        self.data = data

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {"type": self.type, **self.data}


class AgentExecutionService:
    """
    Orchestrates agent conversations with streaming.
    No LangGraph - direct SDK usage.
    Stateful for main agent, stateless for tool LLMs.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.conversation_service = ConversationService(session)
        self.llm_model_service = LLMModelService(session)
        self.tool_registry = ToolRegistry()

    @trace_execution("agent_conversation")
    async def execute_conversation(
        self,
        agent_id: uuid.UUID,
        user_message: str,
        conversation_id: uuid.UUID | None = None,
        user_api_keys: dict[str, str] | None = None,
    ) -> AsyncIterator[ExecutionEvent]:
        """
        Execute agent conversation with streaming.

        Args:
            agent_id: Agent ID to execute
            user_message: User's message
            conversation_id: Existing conversation ID (optional)
            user_api_keys: User-provided API keys for LLM providers

        Yields:
            ExecutionEvent objects for streaming to client
        """
        try:
            # 1. Load agent configuration
            agent = await self._load_agent(agent_id)
            if not agent:
                yield ExecutionEvent("error", error="Agent not found")
                return

            yield ExecutionEvent("agent_loaded", agent_id=str(agent.id))

            # 2. Register agent tools
            await self._register_agent_tools(agent, user_api_keys)

            # 3. Get or create conversation (STATEFUL)
            conversation = await self.conversation_service.get_or_create_conversation(
                agent_id=agent_id, conversation_id=conversation_id, channel_type="test"
            )

            yield ExecutionEvent("conversation_started", conversation_id=str(conversation.id))

            # 4. Save user message
            await self.conversation_service.save_message(
                conversation_id=conversation.id, role="user", content=user_message
            )

            # 5. Build conversation history
            history = await self.conversation_service.get_conversation_history(conversation.id)

            # 6. Get tool schemas
            tool_schemas = await self._get_tool_schemas(agent)

            # DEBUG: Log tool schemas being sent to LLM
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"========== TOOL SCHEMAS FOR LLM ==========")
            for schema in tool_schemas:
                logger.error(f"Tool: {schema.get('name')}")
                logger.error(f"Description: {schema.get('description')}")
                logger.error(f"Input schema: {schema.get('input_schema')}")
            logger.error(f"===========================================")

            # 7. Get LLM provider
            provider_type = agent.model_config.get("provider", "anthropic")
            api_key = self._get_api_key(provider_type, user_api_keys)

            # Check if API key is configured
            if not api_key:
                provider_name = provider_type.capitalize()
                yield ExecutionEvent(
                    "error",
                    error=f"No {provider_name} API key configured. Please add your API key in Settings to enable AI responses.",
                    settings_url="http://localhost:3000/settings"
                )
                return

            provider = LLMProviderFactory.create_provider(provider_type, api_key)

            try:
                # 8. Build enhanced system prompt with tool descriptions
                enhanced_instructions = self._build_enhanced_system_prompt(agent.instructions, tool_schemas)

                # DEBUG: Log enhanced system prompt
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"========== ENHANCED SYSTEM PROMPT ==========")
                logger.error(enhanced_instructions)
                logger.error(f"==========================================")

                # 9. Agentic loop - continue until LLM responds without calling tools
                max_iterations = 5
                iteration = 0
                conversation_messages = history.copy()
                all_tool_calls = []
                final_response_content = ""

                while iteration < max_iterations:
                    iteration += 1

                    # Stream LLM response
                    assistant_content = ""
                    tool_uses = []  # Track tool uses in this turn

                    async for event in provider.stream_with_tools(
                        model=agent.model_config.get("model"),
                        messages=conversation_messages,
                        tools=tool_schemas,
                        system=enhanced_instructions,
                        temperature=agent.model_config.get("temperature", 0.7),
                        max_tokens=agent.model_config.get("max_tokens", 4096),
                    ):
                        if event.type == "content_delta":
                            assistant_content += event.delta
                            # Stream content to user - will determine if this is final response later
                            yield ExecutionEvent("content_delta", delta=event.delta)

                        elif event.type == "tool_use_start":
                            yield ExecutionEvent(
                                "tool_use_start",
                                tool_name=event.tool_name,
                                tool_input=event.tool_input,
                            )

                            # Execute tool
                            start_time = time.time()
                            tool_result = await self._execute_tool(event.tool_name, event.tool_input or {})
                            duration_ms = int((time.time() - start_time) * 1000)

                            # Trace tool execution
                            observability_service.trace_tool_execution(
                                tool_name=event.tool_name,
                                input_data=event.tool_input or {},
                                output_data=tool_result,
                                duration_ms=duration_ms,
                                success=tool_result.get("success", False),
                            )

                            # Track tool use with ID
                            tool_uses.append({
                                "id": event.tool_use_id,
                                "name": event.tool_name,
                                "input": event.tool_input or {},
                                "result": tool_result,
                            })

                            all_tool_calls.append({
                                "tool_name": event.tool_name,
                                "input": event.tool_input,
                                "output": tool_result,
                            })

                            yield ExecutionEvent(
                                "tool_use_complete",
                                tool_name=event.tool_name,
                                result=tool_result,
                            )

                    # If no tools were called, we have the final response
                    if len(tool_uses) == 0:
                        final_response_content = assistant_content
                        break

                    # If tools were called, complete this message before continuing
                    # This creates a separate message bubble for this thinking/tool-calling iteration
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"ITERATION {iteration}: tool_uses={len(tool_uses)}, assistant_content='{assistant_content[:100] if assistant_content else 'EMPTY'}'")

                    if assistant_content:
                        logger.error(f"Sending message_complete after iteration {iteration} with content")
                        yield ExecutionEvent("message_complete", message_id=str(uuid.uuid4()))
                    else:
                        logger.error(f"NOT sending message_complete - no assistant content in iteration {iteration}")

                    # Build messages in provider-specific format
                    if provider_type == "anthropic":
                        # Anthropic format: content blocks with tool_use
                        assistant_message_content = []
                        if assistant_content:
                            assistant_message_content.append({"type": "text", "text": assistant_content})

                        for tool_use in tool_uses:
                            assistant_message_content.append({
                                "type": "tool_use",
                                "id": tool_use["id"],
                                "name": tool_use["name"],
                                "input": tool_use["input"],
                            })

                        conversation_messages.append({
                            "role": "assistant",
                            "content": assistant_message_content,
                        })

                        # Anthropic format: user message with tool_result blocks
                        tool_results_content = []
                        for tool_use in tool_uses:
                            tool_result = tool_use["result"]
                            if isinstance(tool_result, dict) and not tool_result.get("success", True):
                                result_str = tool_result.get("error", str(tool_result))
                            else:
                                result_str = str(tool_result.get("result", tool_result))

                            tool_results_content.append({
                                "type": "tool_result",
                                "tool_use_id": tool_use["id"],
                                "content": result_str,
                            })

                        conversation_messages.append({
                            "role": "user",
                            "content": tool_results_content,
                        })

                    else:
                        # OpenAI/Google format: assistant message with tool_calls
                        import json

                        tool_calls_array = []
                        for tool_use in tool_uses:
                            tool_calls_array.append({
                                "id": tool_use["id"],
                                "type": "function",
                                "function": {
                                    "name": tool_use["name"],
                                    "arguments": json.dumps(tool_use["input"]),
                                }
                            })

                        assistant_msg = {
                            "role": "assistant",
                            "tool_calls": tool_calls_array,
                        }
                        if assistant_content:
                            assistant_msg["content"] = assistant_content
                        else:
                            assistant_msg["content"] = None

                        conversation_messages.append(assistant_msg)

                        # OpenAI/Google format: separate tool messages for each result
                        for tool_use in tool_uses:
                            tool_result = tool_use["result"]
                            if isinstance(tool_result, dict) and not tool_result.get("success", True):
                                result_str = tool_result.get("error", str(tool_result))
                            else:
                                result_str = str(tool_result.get("result", tool_result))

                            conversation_messages.append({
                                "role": "tool",
                                "tool_call_id": tool_use["id"],
                                "content": result_str,
                            })

                    # Continue loop to get next LLM response

                # 9. Save agent response
                await self.conversation_service.save_message(
                    conversation_id=conversation.id,
                    role="agent",
                    content=final_response_content,
                    tool_calls=all_tool_calls,
                )

                # Trace LLM call
                observability_service.trace_llm_call(
                    model=agent.model_config.get("model"),
                    provider=provider_type,
                    input_data={"messages": history, "system": agent.instructions},
                    output_data=final_response_content,
                    metadata={"tool_calls": len(all_tool_calls), "iterations": iteration},
                )

                yield ExecutionEvent("message_complete", message_id=str(uuid.uuid4()))

            finally:
                # Clean up provider
                if hasattr(provider, 'close'):
                    await provider.close()

        except Exception as e:
            error_message = str(e)

            # Check if it's an API key authentication error
            if any(keyword in error_message.lower() for keyword in ["api key", "authentication", "unauthorized", "401", "403"]):
                provider_name = agent.model_config.get("provider", "LLM").capitalize()
                yield ExecutionEvent(
                    "error",
                    error=f"Invalid {provider_name} API key. Please check your API key in Settings.",
                    settings_url="http://localhost:3000/settings"
                )
            else:
                yield ExecutionEvent("error", error=error_message)
        finally:
            # Flush traces
            observability_service.flush()

    async def _load_agent(self, agent_id: uuid.UUID) -> Agent | None:
        """Load agent by ID with relationships eagerly loaded."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from app.models.integration import Integration

        query = (
            select(Agent)
            .where(Agent.id == agent_id)
            .options(selectinload(Agent.integrations).selectinload(Integration.tools))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def _get_tool_schemas(self, agent: Agent) -> list[dict[str, Any]]:
        """Get tool schemas for agent's enabled tools."""
        import logging
        logger = logging.getLogger(__name__)

        tool_schemas = []

        for integration in agent.integrations:
            for tool in integration.tools:
                if tool.is_enabled:
                    # Build schema dynamically - description comes from tool.description, not tool_schema
                    schema = {
                        "name": tool.tool_schema.get("name", tool.name),
                        "description": tool.description or tool.tool_schema.get("description", ""),
                        "input_schema": tool.tool_schema.get("input_schema", {"type": "object", "properties": {}}),
                    }
                    tool_schemas.append(schema)
                    logger.info(f"Adding tool schema for LLM: {tool.name} -> {schema}")

        return tool_schemas

    async def _register_agent_tools(self, agent: Agent, user_api_keys: dict[str, str] | None = None):
        """
        Register all enabled tools for the agent in the tool registry.
        Creates tool instances from database models and registers them.
        """
        import logging
        logger = logging.getLogger(__name__)
        from app.tools.factory import ToolFactory

        # Clear any existing tools for this agent (in case of re-registration)
        # We use tool schema name as the registry key
        for integration in agent.integrations:
            for tool in integration.tools:
                if tool.is_enabled:
                    # Get tool name from schema
                    tool_name = tool.tool_schema.get("name", str(tool.id))
                    logger.info(f"Registering tool: {tool_name}, schema={tool.tool_schema}")

                    # Get API key for LLM tools
                    api_key = None
                    if tool.tool_type == "llm":
                        # Determine provider from the tool's model, not the agent's
                        tool_model = tool.config.get("llm_model", "")
                        provider_type = await self.llm_model_service.get_provider_for_model(tool_model)
                        api_key = self._get_api_key(provider_type, user_api_keys)

                    # Create tool instance
                    tool_instance = ToolFactory.create_tool(tool, api_key=api_key)

                    # Register in registry
                    self.tool_registry.register(tool_name, tool_instance)

    async def _execute_tool(self, tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool by name."""
        tool = self.tool_registry.get(tool_name)

        if not tool:
            return {"success": False, "error": f"Tool {tool_name} not found"}

        try:
            result = await tool.execute(tool_input)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_api_key(self, provider_type: str, user_api_keys: dict[str, str] | None) -> str:
        """Get API key for provider (user-provided or system default)."""
        from app.config import settings

        if user_api_keys and provider_type in user_api_keys:
            return user_api_keys[provider_type]

        # Fallback to system keys
        if provider_type == "anthropic":
            return settings.anthropic_api_key or ""
        elif provider_type == "openai":
            return settings.openai_api_key or ""
        elif provider_type == "google":
            return settings.google_api_key or ""

        raise ValueError(f"No API key found for provider: {provider_type}")

    def _build_enhanced_system_prompt(self, base_instructions: str, tool_schemas: list[dict[str, Any]]) -> str:
        """
        Build enhanced system prompt that includes tool descriptions.
        This helps the LLM understand what tools are available and their required parameters.
        """
        if not tool_schemas:
            return base_instructions

        tools_section = "\n\n# Available Tools\n\nYou have access to the following tools:\n\n"

        for tool_schema in tool_schemas:
            tool_name = tool_schema.get("name", "unknown")
            tool_description = tool_schema.get("description", "No description")
            input_schema = tool_schema.get("input_schema", {})
            properties = input_schema.get("properties", {})
            required_fields = input_schema.get("required", [])

            tools_section += f"## {tool_name}\n"
            tools_section += f"{tool_description}\n\n"

            if properties:
                tools_section += "**Parameters:**\n"
                for param_name, param_info in properties.items():
                    param_type = param_info.get("type", "string")
                    param_desc = param_info.get("description", "")
                    is_required = param_name in required_fields
                    required_marker = " (REQUIRED)" if is_required else " (optional)"

                    tools_section += f"- `{param_name}` ({param_type}){required_marker}: {param_desc}\n"
                tools_section += "\n"
            else:
                tools_section += "No parameters required.\n\n"

        tools_section += "\n**IMPORTANT:** Always provide all REQUIRED parameters when calling tools. Do not call a tool with empty input `{}` if it has required parameters.\n"

        return base_instructions + tools_section
