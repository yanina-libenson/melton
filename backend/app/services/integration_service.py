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

        # Pull any platform credential fields OUT of config so they're stored
        # encrypted (EncryptedCredential), never persisted as plaintext config.
        config = dict(config or {})
        cred_data = self._extract_platform_credentials(platform_id, config)

        integration = Integration(
            agent_id=agent_id,
            type=type,
            platform_id=platform_id,
            name=name,
            description=description,
            config=config,
        )

        self.session.add(integration)
        await self.session.flush()

        if cred_data:
            from app.services.credential_service import CredentialService

            await CredentialService(self.session).store_credentials(integration.id, cred_data)

        await self.session.refresh(integration, ["tools"])

        return integration

    @staticmethod
    def _extract_platform_credentials(platform_id: str | None, config: dict) -> dict | None:
        """Pop a platform's declared credential fields out of `config` and return
        them, so they can be stored encrypted instead of in plaintext config.

        Mutates `config` in place. Returns {field: value} or None if the platform
        declares no credential fields or none are present.
        """
        if not platform_id:
            return None
        from app.tools.platforms.platform_config import PLATFORMS

        platform = PLATFORMS.get(platform_id)
        fields = getattr(platform, "credential_fields", None) if platform else None
        if not fields:
            return None

        data = {f: config.pop(f) for f in fields if f in config}
        return data or None

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
