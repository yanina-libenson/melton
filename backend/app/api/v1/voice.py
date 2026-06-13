"""Voice gateway endpoint: speech in -> agent loop -> speech out.

POST /api/v1/agents/{agent_id}/voice  (multipart: audio file + session_id)
Returns audio/mpeg with headers:
  X-Status: success | needs_confirmation | error
  X-Needs-Confirmation: True | False
  X-Message: the spoken text (header-safe), also the body on the error path.

Same header contract the watch already speaks, so the rewritten watch app just
points here. Voice turns continue a per-(agent, session_id) conversation, so the
confirmation gate works across utterances (say the request, then say "sí").
"""

import json
import logging
import uuid

from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select

from app.config import settings
from app.database import DatabaseSession
from app.dependencies import CurrentUser
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.services.execution_service import AgentExecutionService
from app.services.permission_service import PermissionService
from app.services.user_api_key_service import UserApiKeyService
from app.services.voice_service import VoiceService, VoiceServiceError

router = APIRouter()
logger = logging.getLogger(__name__)


async def _transcription_hint(session, user_id, agent) -> str | None:
    """Build a Whisper prompt from the user's saved contact names so dictated
    names transcribe correctly (e.g. "Yanina" not "Janina"). Scoped exactly like
    the memory tools: (operator user, agent org, agent). Best-effort — any
    failure just means no hint, never a failed transcription."""
    try:
        from app.services.memory_service import MemoryService

        rows = await MemoryService(session).list_all(
            user_id=user_id,
            organization_id=agent.organization_id,
            agent_id=agent.id,
            collection="contactos",
        )
        names = [r.label.strip() for r in rows if (r.label or "").strip()]
        if not names:
            return None
        return "Transferencias en pesos a estos contactos: " + ", ".join(names) + "."
    except Exception:  # noqa: BLE001 — a hint is optional, never block transcription
        logger.warning("Could not build transcription hint from contacts", exc_info=True)
        return None


def _header_safe(text: str) -> str:
    """Make text safe for an HTTP header: drop non-latin-1 (emojis) AND collapse
    control chars like newlines/tabs to spaces (newlines in a header value raise
    'Invalid HTTP header value')."""
    latin1 = text.encode("latin-1", "ignore").decode("latin-1")
    collapsed = "".join(c if c.isprintable() else " " for c in latin1)
    return collapsed[:480]


def _voice_response(
    audio: bytes,
    status_: str,
    needs_confirmation: bool,
    message: str,
    conversation_id: str | None = None,
    transcript: str | None = None,
) -> Response:
    headers = {
        "X-Status": status_,
        "X-Needs-Confirmation": "True" if needs_confirmation else "False",
        "X-Message": _header_safe(message),
    }
    if conversation_id:
        headers["X-Conversation-Id"] = conversation_id
    if transcript:
        headers["X-Transcript"] = _header_safe(transcript)
    if audio:
        return Response(content=audio, media_type="audio/mpeg", headers=headers)
    # Error path: no audio -> JSON body with the same info.
    return Response(
        content=json.dumps(
            {"status": status_, "message": message, "needs_confirmation": needs_confirmation}
        ),
        media_type="application/json",
        headers=headers,
    )


@router.post("/{agent_id}/voice")
async def agent_voice(
    agent_id: uuid.UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
    audio: UploadFile,
    session_id: str = Form("default"),
    conversation_id: str | None = Form(None),
) -> Response:
    user_id = current_user["user_id"]

    agent = (
        await session.execute(select(Agent).where(Agent.id == agent_id))
    ).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    perm = PermissionService(session)
    if not (agent.user_id == user_id or await perm.has_permission(agent_id, user_id)):
        raise HTTPException(status_code=403, detail="You don't have permission for this agent")

    # STT/TTS key: the agent owner's OpenAI key, else the system fallback.
    user_api_keys = await UserApiKeyService(session).get_all_api_keys(
        agent.user_id, agent.organization_id
    )
    openai_key = (user_api_keys or {}).get("openai") or settings.openai_api_key
    if not openai_key:
        return _voice_response(
            b"", "error", False,
            "No hay API key de OpenAI configurada para voz (transcripción y síntesis).",
        )

    voice = VoiceService(api_key=openai_key)

    # 1. Speech -> text (seed Whisper with the user's contact names)
    audio_bytes = await audio.read()
    hint = await _transcription_hint(session, user_id, agent)
    try:
        text = await voice.transcribe(audio_bytes, audio.filename or "audio.m4a", prompt=hint)
    except VoiceServiceError as e:
        return _voice_response(b"", "error", False, f"No pude transcribir el audio: {e}")
    if not text:
        return _voice_response(b"", "error", False, "No entendí el audio, probá de nuevo.")

    # 2. Resolve the conversation. If the client passed a conversation_id (the
    #    UNIFIED case: same thread as the text chat), continue that one. Otherwise
    #    fall back to a per-session "voice" conversation (e.g. the watch).
    conv = None
    if conversation_id:
        try:
            cid = uuid.UUID(conversation_id)
        except ValueError:
            cid = None
        if cid is not None:
            conv = (
                await session.execute(
                    select(Conversation).where(
                        Conversation.id == cid, Conversation.agent_id == agent_id
                    )
                )
            ).scalars().first()
    if conv is None:
        conv = (
            await session.execute(
                select(Conversation)
                .where(
                    Conversation.agent_id == agent_id,
                    Conversation.channel_type == "voice",
                    Conversation.external_user_id == session_id,
                )
                .order_by(Conversation.created_at.desc())
            )
        ).scalars().first()
    if conv is None:
        conv = Conversation(
            agent_id=agent_id, user_id=user_id, channel_type="voice", external_user_id=session_id
        )
        session.add(conv)
        await session.flush()

    # 3. Run the agent loop; accumulate the reply + detect a confirmation gate.
    exec_service = AgentExecutionService(session)
    response_text = ""
    needs_confirmation = False
    confirmation_speech = None
    error_msg = None
    async for ev in exec_service.execute_conversation(
        agent_id=agent_id,
        user_message=text,
        conversation_id=conv.id,
        user_api_keys=user_api_keys,
        user_id=user_id,
    ):
        if ev.type == "content_delta":
            response_text += ev.data.get("delta", "")
        elif ev.type == "confirmation_required":
            needs_confirmation = True
            confirmation_speech = ev.data.get("speech")
        elif ev.type == "error":
            error_msg = ev.data.get("error", "error")
    await session.commit()

    conv_id = str(conv.id)

    if error_msg and not response_text:
        return _voice_response(b"", "error", False, error_msg, conversation_id=conv_id)

    # On a confirmation turn, speak ONLY the tool's terse line (e.g. "Transferir
    # 50.000 pesos a Yanina. ¿Confirmás?") — not the model's narration + summary.
    if needs_confirmation and confirmation_speech and confirmation_speech.strip():
        spoken = confirmation_speech.strip()
    else:
        spoken = response_text.strip() or "Listo."

    # 4. Text -> speech
    try:
        audio_out = await voice.synthesize(spoken)
    except VoiceServiceError:
        # Couldn't synthesize; still return the text so the client can show it.
        return _voice_response(
            b"", "error", needs_confirmation, spoken, conversation_id=conv_id, transcript=text
        )

    return _voice_response(
        audio_out,
        "needs_confirmation" if needs_confirmation else "success",
        needs_confirmation,
        spoken,
        conversation_id=conv_id,
        transcript=text,
    )
