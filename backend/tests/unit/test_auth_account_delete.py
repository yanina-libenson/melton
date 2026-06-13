"""Tests for in-app account deletion (App Store guideline 5.1.1(v))."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import get_database_session
from app.main import app
from app.services.auth_service import AuthService


def _client_with_session(test_session):
    async def _sess():
        yield test_session

    app.dependency_overrides[get_database_session] = _sess
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_delete_account_removes_the_user(test_session):
    email = f"del-{uuid.uuid4().hex}@test.com"
    try:
        async with _client_with_session(test_session) as ac:
            reg = await ac.post(
                "/api/v1/auth/register",
                json={"email": email, "password": "supersecret", "full_name": "Borra Test"},
            )
            assert reg.status_code == 201
            token = reg.json()["access_token"]

            r = await ac.delete(
                "/api/v1/auth/account",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code == 204
    finally:
        app.dependency_overrides.clear()

    # the user is really gone (not just deactivated)
    user_id = AuthService.verify_token(token)["user_id"]
    assert await AuthService(test_session).get_user_by_id(user_id) is None


@pytest.mark.asyncio
async def test_delete_account_requires_auth(test_session, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "debug", False)  # prod behaviour: no token -> 401
    try:
        async with _client_with_session(test_session) as ac:
            r = await ac.delete("/api/v1/auth/account")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 401
