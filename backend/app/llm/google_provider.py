"""Google (Gemini) LLM provider implementation."""

from collections.abc import AsyncIterator
from typing import Any

import google.generativeai as genai

from app.llm.base_provider import BaseLLMProvider, StreamEvent


class GoogleProvider(BaseLLMProvider):
    """Google Gemini provider."""

    def __init__(self, api_key: str):
        super().__init__(api_key)
        genai.configure(api_key=api_key)

    async def stream_with_tools(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[StreamEvent]:
        """Stream Gemini response with function calling."""
        # Convert tools to Gemini format
        gemini_tools = [self.convert_tool_schema(tool) for tool in tools]

        # Create model
        model_instance = genai.GenerativeModel(
            model_name=model,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            },
        )

        # Build prompt from messages
        prompt_parts = []
        if system:
            prompt_parts.append(f"Instructions: {system}\n")

        for msg in messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            prompt_parts.append(f"{role}: {msg['content']}\n")

        prompt = "\n".join(prompt_parts)

        # Stream response
        response = await model_instance.generate_content_async(
            prompt,
            tools=gemini_tools if gemini_tools else None,
            stream=True,
        )

        async for chunk in response:
            if chunk.text:
                yield StreamEvent(event_type="content_delta", delta=chunk.text)

            # Check for function calls
            if hasattr(chunk, "candidates") and chunk.candidates:
                for candidate in chunk.candidates:
                    if hasattr(candidate, "content") and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, "function_call"):
                                yield StreamEvent(
                                    event_type="tool_use_start",
                                    tool_name=part.function_call.name,
                                    tool_input=dict(part.function_call.args),
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
        model_instance = genai.GenerativeModel(
            model_name=model,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            },
        )

        full_prompt = f"Instructions: {system}\n\n{prompt}" if system else prompt

        response = await model_instance.generate_content_async(full_prompt)
        return response.text

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

        model_instance = genai.GenerativeModel(
            model_name=model,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
                "response_mime_type": "application/json",
                "response_schema": output_schema,
            },
        )

        full_prompt = f"Instructions: {system}\n\n{prompt}" if system else prompt

        response = await model_instance.generate_content_async(full_prompt)

        # Parse and return the JSON content
        return json.loads(response.text)

    def convert_tool_schema(self, tool_schema: dict[str, Any]) -> dict[str, Any]:
        """Convert to Gemini function format."""
        return genai.protos.FunctionDeclaration(
            name=tool_schema["name"],
            description=tool_schema["description"],
            parameters=tool_schema.get("input_schema", {"type": "object", "properties": {}}),
        )
