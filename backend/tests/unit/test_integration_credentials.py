"""Tests for encrypted platform-credential storage on integration creation (4 fix 1)."""

import pytest
from sqlalchemy import select

from app.models.encrypted_credential import EncryptedCredential
from app.services.credential_service import CredentialService
from app.services.integration_service import IntegrationService


@pytest.mark.asyncio
async def test_platform_credentials_stored_encrypted_not_in_config(test_session, sample_agent):
    isvc = IntegrationService(test_session)
    integ = await isvc.create_integration(
        agent_id=sample_agent.id,
        type="platform",
        name="Transferir (TelePagos)",
        description=None,
        config={
            "authentication": "credentials",
            "username": "u",
            "password": "super-secret",
            "env": "prod",
        },
        platform_id="telepagos",
    )

    # Credentials must NOT remain in plaintext config...
    assert "password" not in integ.config
    assert "username" not in integ.config
    # ...but non-credential config is preserved.
    assert integ.config.get("authentication") == "credentials"

    # ...and they round-trip through the encrypted store.
    creds = await CredentialService(test_session).get_credentials_dict(integ.id)
    assert creds == {"username": "u", "password": "super-secret", "env": "prod"}

    # The stored value is actually encrypted (the secret is not in cleartext).
    row = (
        await test_session.execute(
            select(EncryptedCredential).where(
                EncryptedCredential.integration_id == integ.id
            )
        )
    ).scalar_one()
    assert "super-secret" not in row.encrypted_value


@pytest.mark.asyncio
async def test_non_platform_integration_config_untouched(test_session, sample_agent):
    isvc = IntegrationService(test_session)
    integ = await isvc.create_integration(
        agent_id=sample_agent.id,
        type="custom-tool",
        name="Custom",
        description=None,
        config={"baseUrl": "https://example.com"},
        platform_id=None,
    )
    assert integ.config == {"baseUrl": "https://example.com"}
    assert await CredentialService(test_session).get_credentials_dict(integ.id) is None
