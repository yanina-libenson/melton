"""Anthropic (Claude) LLM provider implementation."""

from collections.abc import AsyncIterator
from typing import Any

import httpx
from anthropic import AsyncAnthropic

from app.llm.base_provider import BaseLLMProvider, StreamEvent


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider. Direct SDK usage, no LangGraph."""

    def __init__(self, api_key: str):
        super().__init__(api_key)
        # Create a persistent httpx client that we manage ourselves
        # This avoids the AsyncHttpxClientWrapper cleanup issue
        self._httpx_client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=10.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )
        self.client = AsyncAnthropic(
            api_key=api_key,
            max_retries=2,
            http_client=self._httpx_client,
        )

    async def close(self):
        """Explicitly close the clients."""
        try:
            await self._httpx_client.aclose()
        except Exception:
            # Ignore cleanup errors
            pass

    async def stream_with_tools(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[StreamEvent]:
        """Stream Claude response with tool calling."""
        # Convert tools to Anthropic format
        anthropic_tools = [self.convert_tool_schema(tool) for tool in tools]

        async with self.client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system or "",
            messages=messages,
            tools=anthropic_tools,
        ) as stream:
            async for event in stream:
                if event.type == "content_block_delta":
                    if hasattr(event.delta, "text"):
                        yield StreamEvent(event_type="content_delta", delta=event.delta.text)

                elif event.type == "content_block_start":
                    if hasattr(event.content_block, "type") and event.content_block.type == "tool_use":
                        yield StreamEvent(
                            event_type="tool_use_start",
                            tool_name=event.content_block.name,
                            tool_input=event.content_block.input,
                        )

    async def generate_without_tools(
        self,
        model: str,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Generate text without tools (stateless)."""
        message = await self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system or "",
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract text content
        text_content = ""
        for block in message.content:
            if hasattr(block, "text"):
                text_content += block.text

        return text_content

    def convert_tool_schema(self, tool_schema: dict[str, Any]) -> dict[str, Any]:
        """Convert to Anthropic tool format."""
        return {
            "name": tool_schema["name"],
            "description": tool_schema["description"],
            "input_schema": tool_schema.get("input_schema", {"type": "object", "properties": {}}),
        }
