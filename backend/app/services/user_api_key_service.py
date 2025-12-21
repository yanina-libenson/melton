"""User API key service - business logic for managing user LLM provider API keys."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_api_key import UserApiKey
from app.utils.encryption import encryption_service


class UserApiKeyService:
    """Service for managing user API keys. Keeps methods small and focused."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_api_key(
        self,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        provider: str,
        api_key: str,
    ) -> UserApiKey:
        """
        Save or update user API key for a provider.

        Args:
            user_id: User ID
            organization_id: Organization ID
            provider: Provider name ('anthropic', 'openai', 'google')
            api_key: Plaintext API key

        Returns:
            UserApiKey model
        """
        # Check if API key already exists for this user + provider
        existing = await self.get_api_key_record(user_id, organization_id, provider)

        if existing:
            # Update existing
            existing.encrypted_api_key = encryption_service.encrypt(api_key)
            existing.updated_at = datetime.utcnow()
            await self.session.flush()
            await self.session.refresh(existing)
            return existing
        else:
            # Create new
            user_api_key = UserApiKey(
                user_id=user_id,
                organization_id=organization_id,
                provider=provider,
                encrypted_api_key=encryption_service.encrypt(api_key),
            )
            self.session.add(user_api_key)
            await self.session.flush()
            await self.session.refresh(user_api_key)
            return user_api_key

    async def get_api_key_record(
        self, user_id: uuid.UUID, organization_id: uuid.UUID, provider: str
    ) -> UserApiKey | None:
        """Get user API key record for a provider."""
        query = select(UserApiKey).where(
            UserApiKey.user_id == user_id,
            UserApiKey.organization_id == organization_id,
            UserApiKey.provider == provider,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_api_key(
        self, user_id: uuid.UUID, organization_id: uuid.UUID, provider: str
    ) -> str | None:
        """
        Get decrypted API key for a provider.

        Args:
            user_id: User ID
            organization_id: Organization ID
            provider: Provider name

        Returns:
            Decrypted API key or None if not found
        """
        record = await self.get_api_key_record(user_id, organization_id, provider)
        if not record:
            return None
        return encryption_service.decrypt(record.encrypted_api_key)

    async def get_all_api_keys(
        self, user_id: uuid.UUID, organization_id: uuid.UUID
    ) -> dict[str, str]:
        """
        Get all user API keys as a dictionary.

        Args:
            user_id: User ID
            organization_id: Organization ID

        Returns:
            Dictionary mapping provider name to decrypted API key
        """
        query = select(UserApiKey).where(
            UserApiKey.user_id == user_id,
            UserApiKey.organization_id == organization_id,
        )
        result = await self.session.execute(query)
        records = result.scalars().all()

        return {
            record.provider: encryption_service.decrypt(record.encrypted_api_key)
            for record in records
        }

    async def delete_api_key(
        self, user_id: uuid.UUID, organization_id: uuid.UUID, provider: str
    ) -> bool:
        """Delete user API key for a provider."""
        record = await self.get_api_key_record(user_id, organization_id, provider)
        if not record:
            return False

        await self.session.delete(record)
        await self.session.flush()
        return True
