"""OpenAI Whisper STT client — accepts a raw audio blob and returns text.

Whisper handles English with embedded Te Reo proper nouns well (it was
trained on a multilingual corpus). For very accent-heavy audio we'd reach
for a domain-specific recogniser, but for tour-guide questions Whisper is
the right tradeoff between latency, accuracy, and cost for this demo.
"""

from __future__ import annotations

import logging
from io import BytesIO

from openai import AsyncOpenAI

log = logging.getLogger(__name__)


class WhisperClient:
    def __init__(self, *, api_key: str, model: str = "whisper-1") -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        """Transcribe an audio blob to text.

        Whisper accepts most browser-recordable formats (webm, ogg, mp3, m4a,
        wav). We pass the original filename so OpenAI can sniff the format
        without us re-encoding.
        """
        if not audio_bytes:
            return ""

        buffer = BytesIO(audio_bytes)
        buffer.name = filename  # OpenAI SDK uses .name to detect MIME type

        response = await self._client.audio.transcriptions.create(
            model=self.model,
            file=buffer,
            # Bias the recogniser slightly towards Te Reo proper nouns we
            # expect in this demo — Whisper's "prompt" parameter is a soft
            # vocabulary hint, not a strict whitelist.
            prompt=(
                "Aotearoa, Tāmaki Makaurau, Wai-O-Tapu, Tongariro, Aoraki, "
                "Hokitika, Waiheke, Cape Reinga, Milford Sound, Piopiotahi."
            ),
        )
        return (response.text or "").strip()
