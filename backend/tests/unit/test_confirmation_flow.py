"""End-to-end loop test for the confirmation gate (Phase 1, step 3c).

Uses a fake LLM provider and a fake requires_confirmation tool, so it exercises
the real execute_conversation loop with no LLM call and no real money:
  turn 1: LLM calls the tool -> loop SUSPENDS (confirmation_required), tool NOT run
  turn 2: user says "sí"  -> approve exactly-once, tool runs exactly once
  turn 3: user says "sí" again -> no pending, treated as a normal message
"""

import uuid
from typing import Any

import pytest

from app.llm.factory import LLMProviderFactory
from app.services.confirmation_service import ConfirmationService
from app.services.execution_service import AgentExecutionService
from app.tools.base_tool import BaseTool
from app.tools.registry import ToolRegistry


class _FakeConfirmTool(BaseTool):
    requires_confirmation = True

    def __init__(self):
        super().__init__("transfer_money", {"name": "transfer_money", "description": "x"})
        self.executions = 0
        self.last_input: dict | None = None

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        self.executions += 1
        self.last_input = input_data
        return {"success": True, "message": "✅ Transferí $1", "id": "TX-1"}

    def get_schema(self) -> dict[str, Any]:
        return {"name": "transfer_money", "description": "x", "input_schema": {"type": "object", "properties": {}}}

    def confirmation_summary(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return {"amount": input_data.get("amount"), "destino": input_data.get("alias")}


class _Ev:
    def __init__(self, type: str, **kw):
        self.type = type
        self.delta = kw.get("delta", "")
        self.tool_name = kw.get("tool_name")
        self.tool_use_id = kw.get("tool_use_id")
        self.tool_input = kw.get("tool_input")


class _FakeProvider:
    """Yields a scripted list of events per stream_with_tools call."""

    def __init__(self, scripts: list[list[_Ev]]):
        self.scripts = scripts
        self.calls = 0

    async def stream_with_tools(self, **kwargs):
        script = self.scripts[min(self.calls, len(self.scripts) - 1)]
        self.calls += 1
        for ev in script:
            yield ev

    async def close(self):
        pass


def _wire(svc: AgentExecutionService, tool: _FakeConfirmTool, provider: _FakeProvider, monkeypatch):
    async def fake_register(agent, registry: ToolRegistry, user_api_keys=None):
        registry.register("transfer_money", tool)

    async def fake_schemas(agent):
        return [tool.get_schema()]

    monkeypatch.setattr(svc, "_register_agent_tools", fake_register)
    monkeypatch.setattr(svc, "_get_tool_schemas", fake_schemas)
    monkeypatch.setattr(svc, "_get_api_key", lambda *a, **k: "fake-key")
    monkeypatch.setattr(
        LLMProviderFactory, "create_provider", staticmethod(lambda *a, **k: provider)
    )


async def _drain(agen):
    return [ev async for ev in agen]


@pytest.mark.asyncio
async def test_confirmation_gate_suspend_approve_exactly_once(
    test_session, sample_agent, monkeypatch
):
    tool = _FakeConfirmTool()
    provider = _FakeProvider([
        # turn 1: model emits some text then calls the money tool
        [
            _Ev("content_delta", delta="Voy a transferir $1 a yani.mp."),
            _Ev("tool_use_start", tool_name="transfer_money", tool_use_id="toolu_1",
                tool_input={"amount": 1, "alias": "yani.mp"}),
        ],
        # turn 3 (post-approval, normal message): plain text, no tool
        [_Ev("content_delta", delta="Ya estaba hecho.")],
    ])
    svc = AgentExecutionService(test_session)
    _wire(svc, tool, provider, monkeypatch)

    # --- turn 1: should SUSPEND, not execute ---
    events = await _drain(svc.execute_conversation(agent_id=sample_agent.id, user_message="transferí 1 peso a yani mp"))
    types = [e.type for e in events]
    assert "confirmation_required" in types
    conv_id = next(e.data["conversation_id"] for e in events if e.type == "conversation_started")
    assert tool.executions == 0, "tool must NOT run before confirmation"

    pending = await ConfirmationService(test_session).get_pending(uuid.UUID(conv_id))
    assert pending is not None and pending.status == "pending"

    # --- turn 2: 'sí' -> approve + execute exactly once ---
    events2 = await _drain(svc.execute_conversation(
        agent_id=sample_agent.id, user_message="sí, dale", conversation_id=uuid.UUID(conv_id)
    ))
    assert tool.executions == 1, "tool must run exactly once after approval"
    assert tool.last_input.get("reference_id") == pending.reference_id  # idempotency key passed through
    assert any(e.type == "tool_use_complete" for e in events2)
    assert await ConfirmationService(test_session).get_pending(uuid.UUID(conv_id)) is None

    # --- turn 3: another 'sí' -> no pending, normal message, NO re-execution ---
    await _drain(svc.execute_conversation(
        agent_id=sample_agent.id, user_message="sí", conversation_id=uuid.UUID(conv_id)
    ))
    assert tool.executions == 1, "replayed approval must not execute again"


@pytest.mark.asyncio
async def test_confirmation_gate_reject_does_not_execute(
    test_session, sample_agent, monkeypatch
):
    tool = _FakeConfirmTool()
    provider = _FakeProvider([
        [_Ev("tool_use_start", tool_name="transfer_money", tool_use_id="toolu_1",
             tool_input={"amount": 5, "alias": "x.y"})],
    ])
    svc = AgentExecutionService(test_session)
    _wire(svc, tool, provider, monkeypatch)

    events = await _drain(svc.execute_conversation(agent_id=sample_agent.id, user_message="mandá 5"))
    conv_id = next(e.data["conversation_id"] for e in events if e.type == "conversation_started")
    assert "confirmation_required" in [e.type for e in events]

    # reject
    await _drain(svc.execute_conversation(
        agent_id=sample_agent.id, user_message="no, mejor no", conversation_id=uuid.UUID(conv_id)
    ))
    assert tool.executions == 0, "reject must never execute the tool"
    assert await ConfirmationService(test_session).get_pending(uuid.UUID(conv_id)) is None
