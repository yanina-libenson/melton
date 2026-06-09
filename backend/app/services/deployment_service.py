"""Deployment service - business logic for channel deployments.

A deployment row means "this agent is published on this channel". An agent is
considered ACTIVE when it has at least one active deployment (see Agent.is_active).
The mobile and apple_watch apps only list agents deployed on their channel.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deployment import Deployment

# The channels an agent can be deployed to. "web" = embeddable live-chat widget.
DEPLOYMENT_CHANNELS: set[str] = {"web", "whatsapp", "email", "mobile", "apple_watch"}


class DeploymentService:
    """CRUD for an agent's channel deployments."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_for_agent(self, agent_id: uuid.UUID) -> list[Deployment]:
        query = (
            select(Deployment)
            .where(Deployment.agent_id == agent_id)
            .order_by(Deployment.channel_type)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def _get(self, agent_id: uuid.UUID, channel: str) -> Deployment | None:
        query = select(Deployment).where(
            Deployment.agent_id == agent_id, Deployment.channel_type == channel
        )
        return (await self.session.execute(query)).scalar_one_or_none()

    async def deploy(
        self, agent_id: uuid.UUID, channel: str, config: dict | None = None
    ) -> Deployment:
        """Deploy the agent to a channel (idempotent upsert, is_active=True)."""
        existing = await self._get(agent_id, channel)
        if existing:
            existing.is_active = True
            if config is not None:
                existing.config = config
            await self.session.flush()
            await self.session.refresh(existing)
            return existing

        deployment = Deployment(
            agent_id=agent_id,
            channel_type=channel,
            is_active=True,
            config=config or {},
        )
        self.session.add(deployment)
        await self.session.flush()
        await self.session.refresh(deployment)
        return deployment

    async def undeploy(self, agent_id: uuid.UUID, channel: str) -> bool:
        """Remove the agent's deployment on a channel. True if one was removed."""
        existing = await self._get(agent_id, channel)
        if not existing:
            return False
        await self.session.delete(existing)
        await self.session.flush()
        return True
