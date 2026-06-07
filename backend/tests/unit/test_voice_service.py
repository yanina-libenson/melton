"""Tests for VoiceService STT/TTS (Phase 5 voice gateway) — mocked, no network."""

from types import SimpleNamespace

import pytest

from app.services.voice_service import VoiceService, VoiceServiceError


def _fake_client(*, text="hola", audio=b"MP3BYTES", fail_stt=False, fail_tts=False):
    async def transcribe_create(model, file, language):
        if fail_stt:
            raise RuntimeError("boom")
        # echo back so we can assert the filename/format reached the API
        return SimpleNamespace(text=text)

    async def speech_create(model, voice, input):
        if fail_tts:
            raise RuntimeError("boom")
        return SimpleNamespace(content=audio)

    return SimpleNamespace(
        audio=SimpleNamespace(
            transcriptions=SimpleNamespace(create=transcribe_create),
            speech=SimpleNamespace(create=speech_create),
        )
    )


@pytest.mark.asyncio
async def test_transcribe_returns_text():
    vs = VoiceService(client=_fake_client(text="transferí 1 peso"))
    assert await vs.transcribe(b"audio") == "transferí 1 peso"


@pytest.mark.asyncio
async def test_transcribe_applies_es_correction():
    vs = VoiceService(client=_fake_client(text="cambialo"))
    assert await vs.transcribe(b"audio") == "envialo"


@pytest.mark.asyncio
async def test_synthesize_returns_bytes():
    vs = VoiceService(client=_fake_client(audio=b"\x00\x01mp3"))
    assert await vs.synthesize("hola") == b"\x00\x01mp3"


@pytest.mark.asyncio
async def test_stt_failure_raises():
    vs = VoiceService(client=_fake_client(fail_stt=True))
    with pytest.raises(VoiceServiceError):
        await vs.transcribe(b"audio")


@pytest.mark.asyncio
async def test_tts_failure_raises():
    vs = VoiceService(client=_fake_client(fail_tts=True))
    with pytest.raises(VoiceServiceError):
        await vs.synthesize("hola")
