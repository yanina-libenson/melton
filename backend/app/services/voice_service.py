"""Voice gateway: speech-to-text and text-to-speech for agent voice turns.

STT/TTS via OpenAI (Whisper + TTS). The OpenAI client is injectable so tests
never hit the network. Argentine-Spanish transcription corrections are ported
from ai-agent-v2.
"""

import io
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Common Whisper mis-hears in rioplatense Spanish -> intended word.
_ES_CORRECTIONS = {
    "cambialo": "envialo",
    "cámbialo": "envialo",
    "mandalo": "mandalo",
    "hazlo": "hacelo",
}


def _correct_es(text: str) -> str:
    out = text
    for wrong, right in _ES_CORRECTIONS.items():
        out = out.replace(wrong, right)
    return out


class VoiceServiceError(Exception):
    """STT/TTS failure."""


class VoiceService:
    """Speech-to-text and text-to-speech via OpenAI (client injectable)."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        client: Any | None = None,
        stt_model: str = "whisper-1",
        tts_model: str = "tts-1",
        tts_voice: str = "alloy",
    ):
        if client is not None:
            self._client = client
        else:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(api_key=api_key or "")
        self._stt_model = stt_model
        self._tts_model = tts_model
        self._tts_voice = tts_voice

    async def transcribe(
        self, audio_bytes: bytes, filename: str = "audio.m4a", language: str = "es"
    ) -> str:
        """Transcribe audio bytes to text."""
        buf = io.BytesIO(audio_bytes)
        buf.name = filename  # OpenAI infers format from the filename extension
        try:
            resp = await self._client.audio.transcriptions.create(
                model=self._stt_model, file=buf, language=language
            )
        except Exception as e:  # noqa: BLE001
            raise VoiceServiceError(f"STT failed: {e}") from e
        text = (getattr(resp, "text", None) or "").strip()
        return _correct_es(text)

    async def synthesize(self, text: str) -> bytes:
        """Synthesize speech audio (mp3 bytes) from text."""
        try:
            resp = await self._client.audio.speech.create(
                model=self._tts_model, voice=self._tts_voice, input=text or " "
            )
        except Exception as e:  # noqa: BLE001
            raise VoiceServiceError(f"TTS failed: {e}") from e
        # openai>=1 returns an HttpxBinaryResponseContent; .content is the bytes.
        data = getattr(resp, "content", None)
        if data is None and hasattr(resp, "read"):
            data = resp.read()
        return data or b""
