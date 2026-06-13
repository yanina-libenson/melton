"""Tests for the voice gateway endpoint (Phase 5) — mocked STT/TTS + execution."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.database import get_database_session
from app.dependencies import get_current_user
from app.main import app
from app.services.execution_service import AgentExecutionService, ExecutionEvent


def test_header_safe_strips_newlines_and_emojis():
    from app.api.v1.voice import _header_safe

    out = _header_safe("📋 Esto:\n• Monto: $1\twab ✅")
    assert "\n" not in out and "\r" not in out and "\t" not in out  # no control chars
    assert "📋" not in out and "✅" not in out  # emojis dropped (non-latin-1)
    assert "Monto: $1" in out  # accents/text preserved


class _FakeVoice:
    def __init__(self, *a, **k):
        pass

    async def transcribe(self, audio_bytes, filename="audio.m4a", language="es", prompt=None):
        return "transferí 1 peso a yani.mp"

    async def synthesize(self, text):
        return b"FAKE_MP3_BYTES"


def _wire(monkeypatch, test_session, sample_agent, events):
    monkeypatch.setattr(settings, "openai_api_key", "test-openai-key")
    monkeypatch.setattr("app.api.v1.voice.VoiceService", _FakeVoice)

    captured = {}

    async def fake_exec(self, *, agent_id, user_message, conversation_id=None,
                        user_api_keys=None, attachments=None, user_id=None):
        captured["user_message"] = user_message
        captured["conversation_id"] = conversation_id
        for ev in events(conversation_id):
            yield ev

    monkeypatch.setattr(AgentExecutionService, "execute_conversation", fake_exec)

    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": sample_agent.user_id,
        "organization_id": sample_agent.organization_id,
    }

    async def _sess():
        yield test_session

    app.dependency_overrides[get_database_session] = _sess
    return captured


async def _post_voice(agent_id, session_id="s1"):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        return await ac.post(
            f"/api/v1/agents/{agent_id}/voice",
            files={"audio": ("a.m4a", b"rawaudio", "audio/m4a")},
            data={"session_id": session_id},
        )


@pytest.mark.asyncio
async def test_voice_success(test_session, sample_agent, monkeypatch):
    def events(conv_id):
        return [
            ExecutionEvent("conversation_started", conversation_id=str(conv_id)),
            ExecutionEvent("content_delta", delta="Listo, ¿algo más?"),
            ExecutionEvent("message_complete", message_id="m1"),
        ]

    captured = _wire(monkeypatch, test_session, sample_agent, events)
    try:
        r = await _post_voice(sample_agent.id)
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    assert r.content == b"FAKE_MP3_BYTES"
    assert r.headers["content-type"] == "audio/mpeg"
    assert r.headers["x-status"] == "success"
    assert r.headers["x-needs-confirmation"] == "False"
    # the transcription drove the conversation
    assert captured["user_message"] == "transferí 1 peso a yani.mp"


@pytest.mark.asyncio
async def test_voice_confirmation_required(test_session, sample_agent, monkeypatch):
    def events(conv_id):
        return [
            ExecutionEvent("conversation_started", conversation_id=str(conv_id)),
            ExecutionEvent("content_delta", delta="Voy a transferir $1. ¿Confirmás?"),
            ExecutionEvent("confirmation_required", tool_name="transfer_money", summary={}),
            ExecutionEvent("message_complete", message_id="m1"),
        ]

    _wire(monkeypatch, test_session, sample_agent, events)
    try:
        r = await _post_voice(sample_agent.id)
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    assert r.content == b"FAKE_MP3_BYTES"
    assert r.headers["x-status"] == "needs_confirmation"
    assert r.headers["x-needs-confirmation"] == "True"


@pytest.mark.asyncio
async def test_voice_confirmation_speaks_terse_line(test_session, sample_agent, monkeypatch):
    """On a confirmation turn, the watch speaks the tool's terse line — not the
    model's verbose narration nor the bullet summary."""
    terse = "Transferir 1 peso a Yanina Libenson. ¿Confirmás?"

    def events(conv_id):
        return [
            ExecutionEvent("content_delta", delta="Perfecto, voy a preparar la transferencia de 1 peso al alias yani.mp con CUIT ..."),
            ExecutionEvent("confirmation_required", tool_name="transfer_money", summary={}, speech=terse),
            ExecutionEvent("message_complete", message_id="m1"),
        ]

    _wire(monkeypatch, test_session, sample_agent, events)
    try:
        r = await _post_voice(sample_agent.id)
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    assert r.headers["x-status"] == "needs_confirmation"
    assert r.headers["x-message"] == terse  # only the terse line is spoken
    assert "alias" not in r.headers["x-message"]  # narration dropped


@pytest.mark.asyncio
async def test_voice_unifies_with_passed_conversation_id(test_session, sample_agent, monkeypatch):
    """When the client passes conversation_id (the unified text+voice thread),
    the voice turn continues THAT conversation and echoes it back."""
    from app.models.conversation import Conversation

    conv = Conversation(agent_id=sample_agent.id, channel_type="playground")
    test_session.add(conv)
    await test_session.flush()
    cid = str(conv.id)

    def events(conv_id):
        return [
            ExecutionEvent("conversation_started", conversation_id=str(conv_id)),
            ExecutionEvent("content_delta", delta="ok"),
            ExecutionEvent("message_complete", message_id="m1"),
        ]

    captured = _wire(monkeypatch, test_session, sample_agent, events)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post(
                f"/api/v1/agents/{sample_agent.id}/voice",
                files={"audio": ("a.m4a", b"rawaudio", "audio/m4a")},
                data={"session_id": "s1", "conversation_id": cid},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    assert r.headers["x-conversation-id"] == cid
    assert str(captured["conversation_id"]) == cid


@pytest.mark.asyncio
async def test_voice_no_openai_key_returns_error(test_session, sample_agent, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr("app.api.v1.voice.VoiceService", _FakeVoice)
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": sample_agent.user_id,
        "organization_id": sample_agent.organization_id,
    }

    async def _sess():
        yield test_session

    app.dependency_overrides[get_database_session] = _sess
    try:
        r = await _post_voice(sample_agent.id)
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    assert r.headers["x-status"] == "error"
    assert "OpenAI" in r.headers["x-message"]
