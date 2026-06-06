"""Tests for the confirmation pause/resume state machine (Phase 1, step 3b)."""

import uuid
from datetime import datetime

import pytest

from app.services.confirmation_service import ConfirmationService
from app.services.conversation_service import ConversationService


async def _make_conversation(session, agent):
    conv_service = ConversationService(session)
    return await conv_service.get_or_create_conversation(
        agent_id=agent.id, conversation_id=None
    )


def _pending_kwargs(conversation_id):
    return dict(
        conversation_id=conversation_id,
        tool_use_id="toolu_" + uuid.uuid4().hex[:8],
        tool_name="transfer_money",
        tool_args={"amount": 1, "alias": "yani.mp"},
        reference_id=uuid.uuid4().hex,
        summary={"amount": 1, "destino": "yani.mp"},
    )


@pytest.mark.asyncio
async def test_create_and_get_pending(test_session, sample_agent):
    conv = await _make_conversation(test_session, sample_agent)
    svc = ConfirmationService(test_session)

    created = await svc.create_pending(**_pending_kwargs(conv.id))
    assert created.status == "pending"
    assert created.expires_at is not None

    pending = await svc.get_pending(conv.id)
    assert pending is not None
    assert pending.id == created.id
    assert pending.tool_name == "transfer_money"


@pytest.mark.asyncio
async def test_approve_is_exactly_once(test_session, sample_agent):
    """The core money-safety property: approve transitions exactly once."""
    conv = await _make_conversation(test_session, sample_agent)
    svc = ConfirmationService(test_session)
    created = await svc.create_pending(**_pending_kwargs(conv.id))

    assert await svc.approve(created.id) is True   # first wins
    assert await svc.approve(created.id) is False  # replay/double-tap is a no-op

    # No longer pending.
    assert await svc.get_pending(conv.id) is None


@pytest.mark.asyncio
async def test_reject(test_session, sample_agent):
    conv = await _make_conversation(test_session, sample_agent)
    svc = ConfirmationService(test_session)
    created = await svc.create_pending(**_pending_kwargs(conv.id))

    assert await svc.reject(created.id) is True
    assert await svc.reject(created.id) is False
    assert await svc.approve(created.id) is False  # can't approve a rejected one
    assert await svc.get_pending(conv.id) is None


@pytest.mark.asyncio
async def test_expired_is_not_returned_or_approvable(test_session, sample_agent):
    conv = await _make_conversation(test_session, sample_agent)
    svc = ConfirmationService(test_session)
    created = await svc.create_pending(ttl_seconds=-1, **_pending_kwargs(conv.id))

    # Already past expiry: cannot be approved...
    assert await svc.approve(created.id) is False
    # ...and get_pending lazily marks it expired and returns nothing.
    assert await svc.get_pending(conv.id) is None


@pytest.mark.asyncio
async def test_get_pending_none_when_empty(test_session, sample_agent):
    conv = await _make_conversation(test_session, sample_agent)
    svc = ConfirmationService(test_session)
    assert await svc.get_pending(conv.id) is None
