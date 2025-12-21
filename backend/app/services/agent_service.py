"""Agent service - business logic for agent operations."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentUpdate


class AgentService:
    """Service for managing agents. Keeps methods small and focused."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_agent(
        self, user_id: uuid.UUID, organization_id: uuid.UUID, agent_data: AgentCreate
    ) -> Agent:
        """Create a new agent."""
        agent = Agent(
            user_id=user_id,
            organization_id=organization_id,
            name=agent_data.name,
            instructions=agent_data.instructions,
            status=agent_data.status,
            model_config=agent_data.llm_config.model_dump(),
        )

        self.session.add(agent)
        await self.session.flush()
        await self.session.refresh(agent, ["integrations"])

        return agent

    async def get_agent_by_id(self, agent_id: uuid.UUID) -> Agent | None:
        """Get agent by ID with integrations loaded."""
        query = (
            select(Agent)
            .where(Agent.id == agent_id)
            .options(selectinload(Agent.integrations))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_agents_for_user(
        self, user_id: uuid.UUID, organization_id: uuid.UUID
    ) -> list[Agent]:
        """List all agents for a user."""
        query = (
            select(Agent)
            .where(Agent.user_id == user_id, Agent.organization_id == organization_id)
            .options(selectinload(Agent.integrations))
            .order_by(Agent.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_agent(
        self, agent_id: uuid.UUID, agent_data: AgentUpdate
    ) -> Agent | None:
        """Update an existing agent."""
        agent = await self.get_agent_by_id(agent_id)
        if not agent:
            return None

        update_data = agent_data.model_dump(exclude_unset=True)

        # Convert model_config to dict if present
        if "model_config" in update_data and update_data["model_config"]:
            update_data["model_config"] = update_data["model_config"].model_dump()

        for field, value in update_data.items():
            setattr(agent, field, value)

        agent.updated_at = datetime.utcnow()
        await self.session.flush()
        await self.session.refresh(agent)

        return agent

    async def delete_agent(self, agent_id: uuid.UUID) -> bool:
        """Delete an agent."""
        agent = await self.get_agent_by_id(agent_id)
        if not agent:
            return False

        await self.session.delete(agent)
        await self.session.flush()
        return True
