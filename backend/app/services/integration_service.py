"""Integration service for managing integrations."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.integration import Integration
from app.models.agent import Agent


class IntegrationService:
    """Service for managing integrations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_integration(
        self,
        agent_id: uuid.UUID,
        type: str,
        name: str,
        description: str | None,
        config: dict,
        platform_id: str | None = None,
    ) -> Integration:
        """Create a new integration."""
        # Verify agent exists
        result = await self.session.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        if not agent:
            raise ValueError(f"Agent with ID {agent_id} not found")

        integration = Integration(
            agent_id=agent_id,
            type=type,
            platform_id=platform_id,
            name=name,
            description=description,
            config=config or {},
        )

        self.session.add(integration)
        await self.session.flush()
        await self.session.refresh(integration, ["tools"])

        return integration

    async def get_integration(self, integration_id: uuid.UUID) -> Integration | None:
        """Get an integration by ID."""
        result = await self.session.execute(
            select(Integration)
            .options(selectinload(Integration.tools))
            .where(Integration.id == integration_id)
        )
        return result.scalar_one_or_none()

    async def get_agent_integrations(self, agent_id: uuid.UUID) -> list[Integration]:
        """Get all integrations for an agent."""
        result = await self.session.execute(
            select(Integration)
            .options(selectinload(Integration.tools))
            .where(Integration.agent_id == agent_id)
            .order_by(Integration.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_integration(
        self,
        integration_id: uuid.UUID,
        name: str | None = None,
        description: str | None = None,
        config: dict | None = None,
    ) -> Integration:
        """Update an integration."""
        integration = await self.get_integration(integration_id)
        if not integration:
            raise ValueError(f"Integration with ID {integration_id} not found")

        if name is not None:
            integration.name = name
        if description is not None:
            integration.description = description
        if config is not None:
            integration.config = config

        integration.updated_at = datetime.utcnow()
        await self.session.flush()
        await self.session.refresh(integration, ["tools"])

        return integration

    async def delete_integration(self, integration_id: uuid.UUID) -> None:
        """Delete an integration."""
        integration = await self.get_integration(integration_id)
        if not integration:
            raise ValueError(f"Integration with ID {integration_id} not found")

        await self.session.delete(integration)
        await self.session.flush()
