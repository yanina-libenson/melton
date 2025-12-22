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

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        # Transform schema to meet OpenAI strict mode requirements
        strict_schema = self._make_schema_strict(output_schema)

        try:
            # Try using strict mode with transformed schema
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "response",
                        "strict": True,
                        "schema": strict_schema,
                    },
                },
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Parse and return the JSON content
            content = response.choices[0].message.content or "{}"
            return json.loads(content)

        except Exception as e:
            # If strict mode fails, fallback to flexible json_object mode
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Strict schema mode failed, falling back to json_object: {e}")

            # Enhance system prompt with schema
            schema_description = json.dumps(output_schema, indent=2)
            enhanced_system = f"""{system or ''}

IMPORTANT: You must respond with ONLY a valid JSON object that matches this exact schema:
{schema_description}

Do not include any explanatory text before or after the JSON. Only output the JSON object."""

            messages_fallback = [
                {"role": "system", "content": enhanced_system},
                {"role": "user", "content": prompt}
            ]

            response = await self.client.chat.completions.create(
                model=model,
                messages=messages_fallback,
                response_format={"type": "json_object"},
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Parse and return the JSON content
            content = response.choices[0].message.content or "{}"
            text = content.strip()
            start_idx = text.find('{')
            end_idx = text.rfind('}')
            if start_idx != -1 and end_idx != -1:
                json_str = text[start_idx:end_idx+1]
                return json.loads(json_str)
            return json.loads(text)

    def _make_schema_strict(self, schema: dict[str, Any]) -> dict[str, Any]:
        """
        Transform a JSON schema to meet OpenAI strict mode requirements.
        Recursively adds additionalProperties: false to all objects.
        """
        import copy

        strict_schema = copy.deepcopy(schema)

        def add_additional_properties_false(obj: dict[str, Any]) -> None:
            """Recursively add additionalProperties: false to objects."""
            if isinstance(obj, dict):
                # If this is an object type, add additionalProperties: false
                if obj.get("type") == "object":
                    obj["additionalProperties"] = False

                # Recurse into properties
                if "properties" in obj:
                    for prop_value in obj["properties"].values():
                        add_additional_properties_false(prop_value)

                # Recurse into items (for arrays)
                if "items" in obj:
                    add_additional_properties_false(obj["items"])

                # Recurse into anyOf, oneOf, allOf
                for key in ["anyOf", "oneOf", "allOf"]:
                    if key in obj:
                        for item in obj[key]:
                            add_additional_properties_false(item)

        add_additional_properties_false(strict_schema)
        return strict_schema

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
