"""Agent execution service - orchestrates conversation flow with streaming."""

import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.factory import LLMProviderFactory
from app.models.agent import Agent
from app.services.conversation_service import ConversationService
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

            # 2. Get or create conversation (STATEFUL)
            conversation = await self.conversation_service.get_or_create_conversation(
                agent_id=agent_id, conversation_id=conversation_id
            )

            yield ExecutionEvent("conversation_started", conversation_id=str(conversation.id))

            # 3. Save user message
            await self.conversation_service.save_message(
                conversation_id=conversation.id, role="user", content=user_message
            )

            # 4. Build conversation history
            history = await self.conversation_service.get_conversation_history(conversation.id)

            # 5. Get tool schemas
            tool_schemas = await self._get_tool_schemas(agent)

            # 6. Get LLM provider
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
                # 7. Stream LLM response with tool calling
                agent_response_content = ""
                tool_calls_made = []

                async for event in provider.stream_with_tools(
                    model=agent.model_config.get("model"),
                    messages=history,
                    tools=tool_schemas,
                    system=agent.instructions,
                    temperature=agent.model_config.get("temperature", 0.7),
                    max_tokens=agent.model_config.get("max_tokens", 4096),
                ):
                    if event.type == "content_delta":
                        agent_response_content += event.delta
                        yield ExecutionEvent("content_delta", delta=event.delta)

                    elif event.type == "tool_use_start":
                        yield ExecutionEvent(
                            "tool_use_start",
                            tool_name=event.tool_name,
                            tool_input=event.tool_input,
                        )

                        # Execute tool with timing
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

                        tool_calls_made.append(
                            {
                                "tool_name": event.tool_name,
                                "input": event.tool_input,
                                "output": tool_result,
                            }
                        )

                        yield ExecutionEvent(
                            "tool_use_complete",
                            tool_name=event.tool_name,
                            result=tool_result,
                        )

                # 8. Save agent response
                await self.conversation_service.save_message(
                    conversation_id=conversation.id,
                    role="agent",
                    content=agent_response_content,
                    tool_calls=tool_calls_made,
                )

                # Trace LLM call
                observability_service.trace_llm_call(
                    model=agent.model_config.get("model"),
                    provider=provider_type,
                    input_data={"messages": history, "system": agent.instructions},
                    output_data=agent_response_content,
                    metadata={"tool_calls": len(tool_calls_made)},
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

        query = select(Agent).where(Agent.id == agent_id).options(selectinload(Agent.integrations))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def _get_tool_schemas(self, agent: Agent) -> list[dict[str, Any]]:
        """Get tool schemas for agent's enabled tools."""
        tool_schemas = []

        for integration in agent.integrations:
            for tool in integration.tools:
                if tool.is_enabled:
                    tool_schemas.append(tool.tool_schema)

        return tool_schemas

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
