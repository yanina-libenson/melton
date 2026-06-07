"""Tests for refresh tokens (access/refresh separation + /auth/refresh)."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from jose import JWTError

from app.main import app
from app.services.auth_service import AuthService


def test_refresh_token_roundtrips():
    uid, oid = uuid.uuid4(), uuid.uuid4()
    info = AuthService.verify_refresh_token(AuthService.create_refresh_token(uid, oid))
    assert info["user_id"] == uid and info["organization_id"] == oid


def test_access_token_cannot_be_used_as_refresh():
    at = AuthService.create_access_token(uuid.uuid4(), uuid.uuid4())
    with pytest.raises(JWTError):
        AuthService.verify_refresh_token(at)


def test_refresh_token_cannot_be_used_as_access():
    rt = AuthService.create_refresh_token(uuid.uuid4(), uuid.uuid4())
    with pytest.raises(JWTError):
        AuthService.verify_token(rt)


def test_access_token_still_verifies():
    uid, oid = uuid.uuid4(), uuid.uuid4()
    info = AuthService.verify_token(AuthService.create_access_token(uid, oid))
    assert info["user_id"] == uid and info["organization_id"] == oid


@pytest.mark.asyncio
async def test_refresh_endpoint_issues_new_tokens():
    rt = AuthService.create_refresh_token(uuid.uuid4(), uuid.uuid4())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/api/v1/auth/refresh", json={"refresh_token": rt})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"] and body["refresh_token"]
    # the freshly issued access token is a valid access token
    AuthService.verify_token(body["access_token"])


@pytest.mark.asyncio
async def test_refresh_endpoint_rejects_invalid():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/api/v1/auth/refresh", json={"refresh_token": "not-a-token"})
    assert r.status_code == 401
