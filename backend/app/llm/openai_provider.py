"""OpenAI (GPT) LLM provider implementation."""

from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from app.llm.base_provider import BaseLLMProvider, StreamEvent


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider."""

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.client = AsyncOpenAI(api_key=api_key)

    async def stream_with_tools(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[StreamEvent]:
        """Stream GPT response with function calling."""
        # Convert tools to OpenAI format
        openai_tools = [self.convert_tool_schema(tool) for tool in tools]

        # Add system message to messages if provided
        all_messages = messages.copy()
        if system:
            all_messages.insert(0, {"role": "system", "content": system})

        stream = await self.client.chat.completions.create(
            model=model,
            messages=all_messages,
            tools=openai_tools,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None

            if delta and delta.content:
                yield StreamEvent(event_type="content_delta", delta=delta.content)

            if delta and delta.tool_calls:
                for tool_call in delta.tool_calls:
                    if tool_call.function:
                        import json

                        yield StreamEvent(
                            event_type="tool_use_start",
                            tool_name=tool_call.function.name,
                            tool_input=json.loads(tool_call.function.arguments)
                            if tool_call.function.arguments
                            else {},
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
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response.choices[0].message.content or ""

    def convert_tool_schema(self, tool_schema: dict[str, Any]) -> dict[str, Any]:
        """Convert to OpenAI function format."""
        return {
            "type": "function",
            "function": {
                "name": tool_schema["name"],
                "description": tool_schema["description"],
                "parameters": tool_schema.get("input_schema", {"type": "object", "properties": {}}),
            },
        }
