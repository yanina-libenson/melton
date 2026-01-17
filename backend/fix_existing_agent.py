"""One-time script to update existing agent with default instructions."""

import asyncio
from sqlalchemy import select
from app.database import async_session_maker
from app.models.agent import Agent
from app.services.agent_defaults import build_agent_instructions


async def fix_agent():
    """Update existing agent to include default behavioral instructions."""
    async with async_session_maker() as session:
        # Get all agents
        result = await session.execute(select(Agent))
        agents = result.scalars().all()

        if not agents:
            print("No agents found in database")
            return

        print(f"Found {len(agents)} agent(s)")

        for agent in agents:
            print(f"\nAgent: {agent.name} (ID: {agent.id})")
            print(f"Current instructions: {agent.instructions[:100]}...")

            # Build new instructions with defaults
            new_instructions = build_agent_instructions(agent.instructions or "")

            # Update agent
            agent.instructions = new_instructions
            print(f"✅ Updated with default behavioral instructions")

        # Commit all changes
        await session.commit()
        print(f"\n✅ Successfully updated {len(agents)} agent(s)")


if __name__ == "__main__":
    asyncio.run(fix_agent())
