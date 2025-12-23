"""Test script to verify tool calling with Anthropic API."""
import asyncio
import os
from anthropic import AsyncAnthropic

async def test_weather_tool():
    """Test that Anthropic correctly calls a tool with required parameters."""

    # Tool schema - exactly as stored in database
    tool_schema = {
        "name": "get_weather",
        "description": "Get current temperature of a city in Celsius.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "Name of the city in english"
                }
            },
            "required": ["city"]
        }
    }

    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not found in environment")
        return

    client = AsyncAnthropic(api_key=api_key)

    # User message
    messages = [
        {"role": "user", "content": "what's the temperature in London?"}
    ]

    print("=" * 80)
    print("Testing tool calling with Anthropic API")
    print("=" * 80)
    print(f"\nTool schema:")
    import json
    print(json.dumps(tool_schema, indent=2))
    print(f"\nUser message: {messages[0]['content']}")
    print("\nCalling Anthropic API...")
    print("=" * 80)

    # Call Anthropic API with tool
    async with client.messages.stream(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        temperature=0.7,
        system="Act as if you were in love with the user.",
        messages=messages,
        tools=[tool_schema],
    ) as stream:
        async for event in stream:
            if event.type == "content_block_start" and hasattr(event.content_block, "type"):
                if event.content_block.type == "tool_use":
                    print(f"\n✓ Tool called: {event.content_block.name}")
                    print(f"✓ Tool input: {event.content_block.input}")
                    print(f"✓ Tool ID: {event.content_block.id}")

                    # Check if city parameter was provided
                    if "city" in event.content_block.input:
                        print(f"\n✅ SUCCESS: Tool was called with city='{event.content_block.input['city']}'")
                    else:
                        print(f"\n❌ FAILURE: Tool was called without 'city' parameter")
                        print(f"   Input was: {event.content_block.input}")

            elif event.type == "content_block_delta":
                if hasattr(event.delta, "text"):
                    print(event.delta.text, end="", flush=True)

    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(test_weather_tool())
