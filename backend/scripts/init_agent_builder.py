"""
Initialize the Agent Builder agent with system tools.
This meta-agent helps users create other agents conversationally.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.database import async_session_maker
from app.models.agent import Agent
from app.models.integration import Integration
from app.models.tool import Tool


async def init_agent_builder():
    """Initialize the Agent Builder agent with system tools."""
    async with async_session_maker() as session:
        # Check if Agent Builder already exists
        result = await session.execute(
            select(Agent).where(Agent.name == "Agent Builder")
        )
        existing_agent = result.scalar_one_or_none()

        if existing_agent:
            print(f"✅ Agent Builder already exists with ID: {existing_agent.id}")
            return

        # Get a user to assign this agent to (use the first user)
        result = await session.execute(select(Agent).limit(1))
        first_agent = result.scalar_one_or_none()

        if not first_agent:
            print("❌ No agents found. Please create at least one agent first.")
            return

        user_id = first_agent.user_id
        organization_id = first_agent.organization_id

        print(f"Creating Agent Builder for user {user_id}...")

        # Create Agent Builder agent
        agent_builder = Agent(
            user_id=user_id,
            organization_id=organization_id,
            name="Agent Builder",
            instructions="""You are an expert Agent Builder assistant. Your role is to help users create AI agents conversationally.

## Your Capabilities

You have access to three powerful tools to build agents:

1. **create_agent** - Creates a new agent with name, instructions, and model configuration
2. **create_integration** - Creates an integration (container for tools) for an agent
3. **create_api_tool** - Creates an API tool that can call external APIs
4. **search_web** - Searches the web for documentation and guides

## Workflow for Creating an Agent

When a user wants to create an agent, follow these steps:

### 1. Understand Requirements
Ask clarifying questions:
- "What should your agent do?"
- "What kind of tasks will it handle?"
- "Does it need to call any external APIs or tools?"

### 2. Search for API Documentation (if needed)
If the user mentions a specific API or service:
- Use `search_web` to find the official documentation
- Look for: authentication methods, endpoint URLs, required parameters
- Ask: "Do you have an API key for [service]?"

### 3. Create the Agent
Once you understand the requirements, use `create_agent`:
```json
{
  "name": "Customer Support Agent",
  "instructions": "Detailed instructions about what the agent does...",
  "status": "draft",
  "provider": "anthropic",
  "model": "claude-sonnet-4-5-20250929"
}
```

### 4. Create Integration (if tools are needed)
If the agent needs tools, create an integration first:
```json
{
  "agent_id": "the-agent-id-from-step-3",
  "name": "Google Maps Integration",
  "description": "Provides mapping and location services"
}
```

### 5. Create Tools
For each API the agent needs, create a tool:
```json
{
  "integration_id": "the-integration-id-from-step-4",
  "name": "search_locations",
  "description": "Searches for locations by name",
  "endpoint": "https://maps.googleapis.com/maps/api/place/textsearch/json?query={query}&key={api_key}",
  "method": "GET",
  "authentication": "none",
  "parameters": {
    "query": {
      "type": "string",
      "description": "The search query",
      "required": true
    }
  }
}
```

### 6. Explain API Setup
After creating tools, provide step-by-step instructions for getting API credentials:
- "To use this tool, you'll need to:"
- "1. Go to [service website]"
- "2. Create an account..."
- "3. Generate an API key from..."
- "4. Update the tool configuration with your key"

## Important Guidelines

1. **Be Conversational**: Don't just execute tools - explain what you're doing
2. **Ask Questions**: If anything is unclear, ask before creating
3. **Provide Context**: When you search for documentation, summarize what you found
4. **Test Readiness**: After creating an agent, say: "Your agent is ready! Would you like to test it or make any changes?"
5. **Model Selection**: Default to Claude Sonnet 4.5 unless user requests otherwise

## Example Interaction

User: "I want to create an agent that plans travel itineraries and shows them on a map"

You: "Great idea! Let me help you create a travel planning agent. I'll need to:
1. Create the agent with travel planning capabilities
2. Add a Google Maps tool for visualizations

Do you have a Google Maps API key? If not, I can guide you through getting one."

User: "Yes, I have one: AIzaSy..."

You: *calls create_agent*
"✅ Created your Travel Planning Agent!

Now let me add the mapping capability..."
*calls create_integration*
*calls create_api_tool*

"✅ All set! Your agent can now:
- Plan travel itineraries
- Visualize routes on maps

Would you like to test it?"

Remember: Be helpful, friendly, and guide users through the entire process!""",
            status="active",
            model_config={
                "provider": "anthropic",
                "model": "claude-sonnet-4-5-20250929",
                "temperature": 0.7,
                "max_tokens": 4096,
            },
        )

        session.add(agent_builder)
        await session.flush()
        await session.refresh(agent_builder)

        print(f"✅ Created Agent Builder with ID: {agent_builder.id}")

        # Create System Tools integration
        system_integration = Integration(
            agent_id=agent_builder.id,
            type="builtin",
            platform_id="system",
            name="System Tools",
            description="Built-in tools for creating agents, integrations, and tools",
            config={},
        )

        session.add(system_integration)
        await session.flush()
        await session.refresh(system_integration)

        print(f"✅ Created System Tools integration with ID: {system_integration.id}")

        # Create builtin tools

        # 1. create_agent tool
        create_agent_tool = Tool(
            integration_id=system_integration.id,
            name="create_agent",
            description="Creates a new agent with specified name, instructions, and model configuration. Returns the agent ID for use in subsequent operations.",
            tool_type="builtin",
            tool_schema={
                "name": "create_agent",
                "description": "Creates a new agent with specified name, instructions, and model configuration",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Agent name (required, 1-255 characters)",
                        },
                        "instructions": {
                            "type": "string",
                            "description": "System instructions for the agent (required, minimum 20 characters)",
                        },
                        "status": {
                            "type": "string",
                            "description": "Agent status: 'draft', 'active', or 'inactive' (optional, defaults to 'draft')",
                            "enum": ["draft", "active", "inactive"],
                        },
                        "provider": {
                            "type": "string",
                            "description": "LLM provider: 'anthropic', 'openai', or 'google' (optional, defaults to 'anthropic')",
                            "enum": ["anthropic", "openai", "google"],
                        },
                        "model": {
                            "type": "string",
                            "description": "Model identifier (optional, defaults to 'claude-sonnet-4-5-20250929')",
                        },
                        "temperature": {
                            "type": "number",
                            "description": "Temperature for generation, 0.0-2.0 (optional, defaults to 0.7)",
                        },
                        "max_tokens": {
                            "type": "integer",
                            "description": "Maximum tokens to generate (optional, defaults to 4096)",
                        },
                    },
                    "required": ["name", "instructions"],
                },
            },
            config={"function_name": "create_agent"},
            is_enabled=True,
        )

        # 2. create_integration tool
        create_integration_tool = Tool(
            integration_id=system_integration.id,
            name="create_integration",
            description="Creates a new integration (container for tools) for a specific agent. Required before creating tools. Returns the integration ID.",
            tool_type="builtin",
            tool_schema={
                "name": "create_integration",
                "description": "Creates a new integration (container for tools) for a specific agent",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "ID of the agent to attach this integration to (required)",
                        },
                        "name": {
                            "type": "string",
                            "description": "Integration name (required)",
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of what this integration provides (required)",
                        },
                        "type": {
                            "type": "string",
                            "description": "Integration type (optional, defaults to 'custom')",
                        },
                        "platform_id": {
                            "type": "string",
                            "description": "Platform identifier (optional, defaults to 'custom_api')",
                        },
                    },
                    "required": ["agent_id", "name", "description"],
                },
            },
            config={"function_name": "create_integration"},
            is_enabled=True,
        )

        # 3. create_api_tool tool
        create_api_tool_tool = Tool(
            integration_id=system_integration.id,
            name="create_api_tool",
            description="Creates a new API tool that can call external REST APIs. Supports GET, POST, PUT, PATCH, DELETE methods and various authentication types. Returns the tool ID.",
            tool_type="builtin",
            tool_schema={
                "name": "create_api_tool",
                "description": "Creates a new API tool that can call external REST APIs",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "integration_id": {
                            "type": "string",
                            "description": "ID of the integration to attach this tool to (required)",
                        },
                        "name": {
                            "type": "string",
                            "description": "Tool name - use snake_case (required)",
                        },
                        "description": {
                            "type": "string",
                            "description": "What this tool does (required)",
                        },
                        "endpoint": {
                            "type": "string",
                            "description": "Full API endpoint URL. Can use {param} templates for path/query parameters (required). Example: 'https://api.example.com/search?q={query}&key={api_key}'",
                        },
                        "method": {
                            "type": "string",
                            "description": "HTTP method (optional, defaults to 'GET')",
                            "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                        },
                        "authentication": {
                            "type": "string",
                            "description": "Authentication type (optional, defaults to 'none')",
                            "enum": ["none", "api-key", "bearer", "basic", "oauth"],
                        },
                        "api_key_header": {
                            "type": "string",
                            "description": "Header name for API key, e.g., 'X-API-Key' (optional, used with api-key authentication)",
                        },
                        "api_key_value": {
                            "type": "string",
                            "description": "The actual API key value (optional, used with api-key authentication)",
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Parameter definitions as {param_name: {type, description, required}} (optional)",
                        },
                    },
                    "required": ["integration_id", "name", "description", "endpoint"],
                },
            },
            config={"function_name": "create_api_tool"},
            is_enabled=True,
        )

        session.add_all([create_agent_tool, create_integration_tool, create_api_tool_tool])
        await session.flush()

        print("✅ Created 3 builtin tools: create_agent, create_integration, create_api_tool")

        # Create Web Search integration with API tool using Google Custom Search
        web_search_integration = Integration(
            agent_id=agent_builder.id,
            type="custom",
            platform_id="custom_api",
            name="Web Search",
            description="Search the web for information, documentation, and guides",
            config={
                "baseUrl": "https://www.googleapis.com/customsearch/v1?q={query}&key=YOUR_GOOGLE_API_KEY&cx=YOUR_SEARCH_ENGINE_ID",
                "method": "GET",
                "authentication": "none",
            },
        )

        session.add(web_search_integration)
        await session.flush()
        await session.refresh(web_search_integration)

        print(f"✅ Created Web Search integration with ID: {web_search_integration.id}")

        # Create web search tool
        web_search_tool = Tool(
            integration_id=web_search_integration.id,
            name="search_web",
            description="Searches the web using Google Custom Search. Use this to find API documentation, guides, or any information needed to help users. Returns top search results with titles, snippets, and links.",
            tool_type="api",
            tool_schema={
                "name": "search_web",
                "description": "Searches the web for information, documentation, and guides",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query. Be specific. Example: 'Google Maps Static API documentation'",
                        },
                    },
                    "required": ["query"],
                },
            },
            config={
                "output_mode": "full",
            },
            is_enabled=True,
        )

        session.add(web_search_tool)
        await session.commit()

        print("✅ Created web search tool")
        print("\n" + "=" * 60)
        print("✅ Agent Builder initialization complete!")
        print("=" * 60)
        print(f"\nAgent ID: {agent_builder.id}")
        print(f"\nIMPORTANT: Update the Web Search integration with:")
        print("1. Your Google API key")
        print("2. Your Custom Search Engine ID")
        print("\nGet them at:")
        print("- API Key: https://console.cloud.google.com/apis/credentials")
        print("- Search Engine: https://programmablesearchengine.google.com/")


if __name__ == "__main__":
    asyncio.run(init_agent_builder())
