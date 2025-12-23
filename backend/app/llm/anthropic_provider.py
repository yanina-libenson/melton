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
        import contextlib

        with contextlib.suppress(Exception):
            await self._httpx_client.aclose()

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
        import logging
        logger = logging.getLogger(__name__)

        # Convert tools to Anthropic format
        anthropic_tools = [self.convert_tool_schema(tool) for tool in tools]
        logger.info(f"Sending {len(anthropic_tools)} tools to Anthropic API:")
        for tool in anthropic_tools:
            logger.info(f"  Tool: {tool['name']}")
            logger.info(f"  Input schema: {tool.get('input_schema', {})}")

        # DEBUG: Print to stdout to ensure we see it
        print(f"\n{'='*80}")
        print(f"ANTHROPIC API CALL - Sending {len(anthropic_tools)} tools:")
        for tool in anthropic_tools:
            print(f"  Tool: {tool['name']}")
            print(f"  Description: {tool.get('description', 'N/A')}")
            print(f"  Input schema: {tool.get('input_schema', {})}")
        print(f"{'='*80}\n")

        # DEBUG: Log the messages being sent
        logger.error(f"========== MESSAGES SENT TO CLAUDE ==========")
        logger.error(f"System prompt (first 500 chars): {(system or '')[:500]}")
        logger.error(f"Number of messages: {len(messages)}")
        for i, msg in enumerate(messages):
            logger.error(f"Message {i}: role={msg.get('role')}, content type={type(msg.get('content'))}")
            if isinstance(msg.get('content'), str):
                logger.error(f"  Content (first 200 chars): {msg.get('content')[:200]}")
            elif isinstance(msg.get('content'), list):
                logger.error(f"  Content blocks: {len(msg.get('content'))}")
                for j, block in enumerate(msg.get('content', [])):
                    logger.error(f"    Block {j}: type={block.get('type')}")
        logger.error(f"============================================")

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

                elif (
                    event.type == "content_block_start"
                    and hasattr(event.content_block, "type")
                    and event.content_block.type == "tool_use"
                ):
                    # DEBUG: Log what Claude is actually sending
                    logger.error(f"========== CLAUDE CALLED TOOL ==========")
                    logger.error(f"Tool name: {event.content_block.name}")
                    logger.error(f"Tool input: {event.content_block.input}")
                    logger.error(f"Tool input type: {type(event.content_block.input)}")
                    logger.error(f"Tool ID: {event.content_block.id}")
                    logger.error(f"=======================================")

                    yield StreamEvent(
                        event_type="tool_use_start",
                        tool_name=event.content_block.name,
                        tool_input=event.content_block.input,
                        tool_use_id=event.content_block.id,
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

    async def generate_structured_output(
        self,
        model: str,
        prompt: str,
        output_schema: dict[str, Any],
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Generate structured output matching a JSON schema."""
        import json

        # Build enhanced system prompt with JSON schema instructions
        schema_description = json.dumps(output_schema, indent=2)
        enhanced_system = f"""{system or ''}

IMPORTANT: You must respond with ONLY a valid JSON object that matches this exact schema:
{schema_description}

Do not include any explanatory text before or after the JSON. Only output the JSON object."""

        message = await self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=enhanced_system,
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract and parse JSON content
        for block in message.content:
            if hasattr(block, "text"):
                # Try to extract JSON from the text (in case there's extra text)
                text = block.text.strip()
                # Find JSON object boundaries
                start_idx = text.find('{')
                end_idx = text.rfind('}')
                if start_idx != -1 and end_idx != -1:
                    json_str = text[start_idx:end_idx+1]
                    return json.loads(json_str)
                return json.loads(text)

        return {}

    def convert_tool_schema(self, tool_schema: dict[str, Any]) -> dict[str, Any]:
        """Convert to Anthropic tool format."""
        return {
            "name": tool_schema["name"],
            "description": tool_schema["description"],
            "input_schema": tool_schema.get("input_schema", {"type": "object", "properties": {}}),
        }
