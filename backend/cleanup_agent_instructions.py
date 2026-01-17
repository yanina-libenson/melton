"""Remove default instructions from existing agents (keep only user's custom instructions)."""

import asyncio
from sqlalchemy import select
from app.database import async_session_maker
from app.models.agent import Agent


async def cleanup_agents():
    """Remove default behavioral instructions from agents, keep only user's custom instructions."""
    async with async_session_maker() as session:
        # Get all agents
        result = await session.execute(select(Agent))
        agents = result.scalars().all()

        if not agents:
            print("No agents found in database")
            return

        print(f"Found {len(agents)} agent(s)")

        # The default instructions start with this marker
        DEFAULT_MARKER = "\n\n# Default Agent Instructions Template"

        for agent in agents:
            print(f"\nAgent: {agent.name} (ID: {agent.id})")

            if DEFAULT_MARKER in agent.instructions:
                # Split and keep only the part before the default instructions
                custom_instructions = agent.instructions.split(DEFAULT_MARKER)[0].strip()
                agent.instructions = custom_instructions
                print(f"✅ Removed default instructions, kept: {custom_instructions[:100]}...")
            else:
                print(f"ℹ️  No default instructions found, leaving as is")

        # Commit all changes
        await session.commit()
        print(f"\n✅ Successfully cleaned {len(agents)} agent(s)")


if __name__ == "__main__":
    asyncio.run(cleanup_agents())
