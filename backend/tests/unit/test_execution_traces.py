"""Tests for durable ExecutionTrace persistence (Phase 1, step 2).

The conversation /trace endpoint reads ExecutionTrace rows, but the execution
loop never wrote them. These tests pin the persistence path:
ConversationService.save_execution_traces writes rows linked to a message.
"""

import pytest
from sqlalchemy import select

from app.models.execution_trace import ExecutionTrace
from app.services.conversation_service import ConversationService


@pytest.mark.asyncio
async def test_execution_traces_persisted(test_session, sample_agent):
    """Traces accumulated during a run are persisted and linked to the message."""
    svc = ConversationService(test_session)
    conv = await svc.get_or_create_conversation(
        agent_id=sample_agent.id, conversation_id=None
    )
    msg = await svc.save_message(
        conversation_id=conv.id, role="agent", content="done", tool_calls=[]
    )

    traces = [
        {
            "step_type": "tool_call",
            "step_data": {
                "tool_name": "get_weather",
                "input": {"city": "Buenos Aires"},
                "output": {"success": True, "result": {"temp": 21}},
                "success": True,
            },
            "duration_ms": 12,
        },
        {
            "step_type": "llm_call",
            "step_data": {
                "model": "claude-sonnet-4-20250514",
                "provider": "anthropic",
                "iterations": 1,
                "tool_calls": 1,
            },
            "duration_ms": None,
        },
    ]
    await svc.save_execution_traces(msg.id, traces)

    rows = (
        (
            await test_session.execute(
                select(ExecutionTrace).where(ExecutionTrace.message_id == msg.id)
            )
        )
        .scalars()
        .all()
    )

    assert len(rows) == 2
    assert {r.step_type for r in rows} == {"tool_call", "llm_call"}

    tool_row = next(r for r in rows if r.step_type == "tool_call")
    assert tool_row.step_data["tool_name"] == "get_weather"
    assert tool_row.step_data["success"] is True
    assert tool_row.duration_ms == 12


@pytest.mark.asyncio
async def test_save_execution_traces_empty_is_noop(test_session, sample_agent):
    """An empty trace list writes nothing (no crash, no rows)."""
    svc = ConversationService(test_session)
    conv = await svc.get_or_create_conversation(
        agent_id=sample_agent.id, conversation_id=None
    )
    msg = await svc.save_message(conversation_id=conv.id, role="agent", content="hi")

    await svc.save_execution_traces(msg.id, [])

    rows = (
        (
            await test_session.execute(
                select(ExecutionTrace).where(ExecutionTrace.message_id == msg.id)
            )
        )
        .scalars()
        .all()
    )
    assert rows == []
