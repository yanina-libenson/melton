"""Credential management service for OAuth and API keys."""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.encrypted_credential import EncryptedCredential
from app.utils.encryption import encryption_service


class CredentialService:
    """Service for managing encrypted credentials."""

    def __init__(self, session: AsyncSession):
        """
        Initialize credential service.

        Args:
            session: Database session
        """
        self.session = session

    async def store_oauth_credentials(
        self,
        integration_id: uuid.UUID,
        access_token: str,
        refresh_token: str,
        expires_in: int,
        token_url: str,
    ) -> EncryptedCredential:
        """
        Store OAuth tokens encrypted.

        Args:
            integration_id: Integration ID
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            expires_in: Token expiry in seconds
            token_url: OAuth token endpoint URL

        Returns:
            Created or updated credential record
        """
        # Calculate expiry datetime
        expiry = datetime.utcnow() + timedelta(seconds=expires_in)

        # Encrypt tokens
        encrypted_access = encryption_service.encrypt(access_token)
        encrypted_refresh = encryption_service.encrypt(refresh_token)

        # Check if credential already exists
        stmt = select(EncryptedCredential).where(
            EncryptedCredential.integration_id == integration_id,
            EncryptedCredential.credential_type == "oauth_access_token",
        )
        result = await self.session.execute(stmt)
        credential = result.scalar_one_or_none()

        if credential:
            # Update existing credential
            credential.encrypted_value = encrypted_access
            credential.encrypted_refresh_token = encrypted_refresh
            credential.token_expiry = expiry
            credential.oauth_token_url = token_url
            credential.updated_at = datetime.utcnow()
        else:
            # Create new credential
            credential = EncryptedCredential(
                integration_id=integration_id,
                credential_type="oauth_access_token",
                encrypted_value=encrypted_access,
                encrypted_refresh_token=encrypted_refresh,
                token_expiry=expiry,
                oauth_token_url=token_url,
            )
            self.session.add(credential)

        await self.session.commit()
        await self.session.refresh(credential)
        return credential

    async def get_credentials(
        self, integration_id: uuid.UUID, credential_type: str = "oauth_access_token"
    ) -> EncryptedCredential | None:
        """
        Retrieve credentials for an integration.

        Args:
            integration_id: Integration ID
            credential_type: Type of credential to retrieve

        Returns:
            Credential record or None if not found
        """
        stmt = select(EncryptedCredential).where(
            EncryptedCredential.integration_id == integration_id,
            EncryptedCredential.credential_type == credential_type,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def is_token_expired(self, credential: EncryptedCredential) -> bool:
        """
        Check if access token is expired.

        Args:
            credential: Credential record

        Returns:
            True if token is expired or expiry not set
        """
        if not credential.token_expiry:
            return True

        # Add 60 second buffer to refresh before actual expiry
        return datetime.utcnow() >= (credential.token_expiry - timedelta(seconds=60))

    async def decrypt_token(self, credential: EncryptedCredential) -> str:
        """
        Decrypt access token.

        Args:
            credential: Credential record

        Returns:
            Decrypted access token
        """
        return encryption_service.decrypt(credential.encrypted_value)

    async def decrypt_refresh_token(self, credential: EncryptedCredential) -> str:
        """
        Decrypt refresh token.

        Args:
            credential: Credential record

        Returns:
            Decrypted refresh token

        Raises:
            ValueError: If no refresh token available
        """
        if not credential.encrypted_refresh_token:
            raise ValueError("No refresh token available")
        return encryption_service.decrypt(credential.encrypted_refresh_token)
