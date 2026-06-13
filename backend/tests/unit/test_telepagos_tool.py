"""Tests for TelePagosTransferTool (Phase 1, step 4) — fully mocked, NO real money."""

import uuid

import pytest

from app.models.integration import Integration
from app.tools.platforms.telepagos import TelePagosTransferTool
from app.tools.platforms.telepagos.client import TelePagosError


class _FakeTP:
    """Records the cashout call; never touches the network."""

    instances: list["_FakeTP"] = []

    def __init__(self, username, password, env):
        self.username, self.env = username, env
        self.cashout_calls: list[dict] = []
        _FakeTP.instances.append(self)

    def cashout(self, *, amount, cuit, reference_id, concept, description, cvu, alias):
        self.cashout_calls.append(
            {"amount": amount, "cuit": cuit, "reference_id": reference_id,
             "concept": concept, "cvu": cvu, "alias": alias}
        )
        return "2026-06-06_99999"

    def balance(self):
        return 34

    def close(self):
        pass


class _ErrTP(_FakeTP):
    def cashout(self, **kwargs):
        raise TelePagosError("The alias yani.mp belongs to another holder")


def _make_tool(client_factory=_FakeTP, creds=None):
    integ = Integration(id=uuid.uuid4(), platform_id="telepagos", config={})
    tool = TelePagosTransferTool("tool-1", {}, integ)
    tool.client_factory = client_factory
    _creds = creds if creds is not None else {"username": "u", "password": "p", "env": "prod"}

    async def _fake_creds():
        return _creds

    tool._get_credentials = _fake_creds
    return tool


def test_requires_confirmation():
    assert TelePagosTransferTool.requires_confirmation is True


@pytest.mark.asyncio
async def test_rejects_zero_amount():
    tool = _make_tool()
    res = await tool.execute({"amount": 0, "alias": "yani.mp", "cuit": "27323575954"})
    assert res["success"] is False
    assert "monto" in res["error"].lower()


@pytest.mark.asyncio
async def test_requires_exactly_one_destination():
    tool = _make_tool()
    both = await tool.execute({"amount": 1, "alias": "a.b", "cvu": "0" * 22, "cuit": "27323575954"})
    assert both["success"] is False
    neither = await tool.execute({"amount": 1, "cuit": "27323575954"})
    assert neither["success"] is False


@pytest.mark.asyncio
async def test_requires_cuit():
    tool = _make_tool()
    res = await tool.execute({"amount": 1, "alias": "yani.mp"})
    assert res["success"] is False
    assert "cuit" in res["error"].lower()


@pytest.mark.asyncio
async def test_rejects_above_cap():
    tool = _make_tool()
    res = await tool.execute({"amount": 999_999, "alias": "yani.mp", "cuit": "27323575954"})
    assert res["success"] is False
    assert "tope" in res["error"].lower()


@pytest.mark.asyncio
async def test_missing_credentials():
    tool = _make_tool(creds={})  # no username/password
    res = await tool.execute({"amount": 1, "alias": "yani.mp", "cuit": "27323575954"})
    assert res["success"] is False
    assert "credenciales" in res["error"].lower()


@pytest.mark.asyncio
async def test_successful_transfer_passes_reference_id():
    _FakeTP.instances.clear()
    tool = _make_tool()
    ref = uuid.uuid4().hex
    res = await tool.execute(
        {"amount": 1, "alias": "yani.mp", "cuit": "27323575954", "reference_id": ref}
    )
    assert res["success"] is True
    assert res["id"] == "2026-06-06_99999"
    assert res["reference_id"] == ref
    # the idempotency key was passed through to cashout
    call = _FakeTP.instances[-1].cashout_calls[-1]
    assert call["reference_id"] == ref
    assert call["alias"] == "yani.mp" and call["cvu"] is None
    assert "✅" in res["message"]


def test_confirmation_is_terse_and_in_pesos():
    """Voice confirmation: only amount + name, says 'pesos', no alias/CVU/'$'."""
    integ = Integration(id=uuid.uuid4(), platform_id="telepagos", config={})
    tool = TelePagosTransferTool("tool-1", {}, integ)
    speech = tool.confirmation_speech(
        {"amount": 50000, "alias": "yani.mp", "cuit": "27323575954", "recipient_name": "Yanina Libenson"}
    )
    assert speech == "Transferir 50.000 pesos a Yanina Libenson. ¿Confirmás?"
    assert "yani.mp" not in speech and "$" not in speech and "27323575954" not in speech


def test_confirmation_summary_prefers_name_over_alias():
    integ = Integration(id=uuid.uuid4(), platform_id="telepagos", config={})
    tool = TelePagosTransferTool("tool-1", {}, integ)
    s = tool.confirmation_summary({"amount": 1, "alias": "yani.mp", "recipient_name": "Yanina"})
    assert s["destinatario"] == "Yanina"
    assert "cuit" not in s and "concepto" not in s  # minimal


def test_confirmation_falls_back_to_alias_without_name():
    integ = Integration(id=uuid.uuid4(), platform_id="telepagos", config={})
    tool = TelePagosTransferTool("tool-1", {}, integ)
    speech = tool.confirmation_speech({"amount": 1, "cvu": "0" * 22})
    assert "0000000000000000000000" in speech  # no saved name -> CVU


@pytest.mark.asyncio
async def test_success_message_uses_name_and_pesos():
    _FakeTP.instances.clear()
    tool = _make_tool()
    res = await tool.execute(
        {"amount": 50000, "alias": "yani.mp", "cuit": "27323575954",
         "recipient_name": "Yanina Libenson", "reference_id": uuid.uuid4().hex}
    )
    assert res["success"] is True
    assert "50.000 pesos" in res["message"]
    assert "Yanina Libenson" in res["message"]
    assert "$" not in res["message"]


@pytest.mark.asyncio
async def test_maps_holder_mismatch_error():
    tool = _make_tool(client_factory=_ErrTP)
    res = await tool.execute({"amount": 1, "alias": "yani.mp", "cuit": "20111111112"})
    assert res["success"] is False
    assert "another holder" in res["error"]
    assert "titular" in res["suggestion"].lower()
