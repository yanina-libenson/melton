"""Tests for TelePagosBalanceTool — fully mocked, read-only, no network."""

import uuid

import pytest

from app.models.integration import Integration
from app.tools.platforms.telepagos import TelePagosBalanceTool
from app.tools.platforms.telepagos.client import TelePagosError


class _FakeTP:
    def __init__(self, username, password, env):
        self.username, self.env = username, env

    def balance(self):
        return 1234

    def close(self):
        pass


class _ErrTP(_FakeTP):
    def balance(self):
        raise TelePagosError("Wrong credentials")


def _make_tool(client_factory=_FakeTP, creds=None):
    integ = Integration(id=uuid.uuid4(), platform_id="telepagos", config={})
    tool = TelePagosBalanceTool("tool-bal", {}, integ)
    tool.client_factory = client_factory
    _creds = creds if creds is not None else {"username": "u", "password": "p", "env": "prod"}

    async def _fake_creds():
        return _creds

    tool._get_credentials = _fake_creds
    return tool


def test_balance_does_not_require_confirmation():
    assert TelePagosBalanceTool.requires_confirmation is False


@pytest.mark.asyncio
async def test_balance_success():
    tool = _make_tool()
    res = await tool.execute({})
    assert res["success"] is True
    assert res["balance"] == 1234
    assert "1234" in res["message"]


@pytest.mark.asyncio
async def test_balance_missing_credentials():
    tool = _make_tool(creds={})
    res = await tool.execute({})
    assert res["success"] is False
    assert "credenciales" in res["error"].lower()


@pytest.mark.asyncio
async def test_balance_maps_client_error():
    tool = _make_tool(client_factory=_ErrTP)
    res = await tool.execute({})
    assert res["success"] is False
    assert "credentials" in res["error"].lower()
