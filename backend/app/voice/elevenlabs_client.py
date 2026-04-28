"""ElevenLabs TTS client — streams MP3 audio for Jamie's cloned voice.

We use the streaming endpoint so playback can start before synthesis is
complete. The flow is split into two methods so the FastAPI route can
validate the upstream response *before* the StreamingResponse begins:

  * ``open_stream(text)`` — open the request, validate status, return the
    open client + response. Raises :class:`ElevenLabsError` on 4xx/5xx with
    a parsed status code (e.g. ``"quota_exceeded"``) and human-readable
    message extracted from ElevenLabs' JSON error body.

  * ``stream_chunks(client, response)`` — async iterator that yields MP3
    bytes from the open response, then closes both. Hand this to
    ``StreamingResponse``.
"""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator

import httpx

log = logging.getLogger(__name__)

ELEVENLABS_BASE = "https://api.elevenlabs.io/v1"


class ElevenLabsError(Exception):
    """Structured error from an ElevenLabs API call.

    ``status`` is the machine-readable code from the response body
    (``quota_exceeded``, ``invalid_api_key``, ``missing_permissions``, etc.).
    ``message`` is the human-readable text from the response.
    """

    def __init__(self, status_code: int, status: str | None, message: str) -> None:
        self.status_code = status_code
        self.status = status
        self.message = message
        super().__init__(f"{status_code} {status or '?'}: {message}")


def _parse_error(status_code: int, body: bytes) -> ElevenLabsError:
    """Pull a clean (status, message) pair out of ElevenLabs' JSON error body."""
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        data = None

    if isinstance(data, dict):
        detail = data.get("detail")
        if isinstance(detail, dict):
            return ElevenLabsError(
                status_code=status_code,
                status=detail.get("status"),
                message=str(detail.get("message") or body[:500]),
            )
        if isinstance(detail, str):
            return ElevenLabsError(status_code=status_code, status=None, message=detail)

    return ElevenLabsError(
        status_code=status_code,
        status=None,
        message=body.decode("utf-8", "replace")[:500],
    )


class ElevenLabsClient:
    def __init__(
        self,
        *,
        api_key: str,
        voice_id: str,
        model_id: str = "eleven_multilingual_v2",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.2,
        pronunciation_dictionary_id: str | None = None,
        pronunciation_dictionary_version_id: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.voice_id = voice_id
        self.model_id = model_id
        self.stability = stability
        self.similarity_boost = similarity_boost
        self.style = style
        # Pronunciation dictionary locator (both must be set for it to take
        # effect — see scripts/setup_pronunciation_dict.py for how to create
        # one). When set, every TTS request references the dictionary so
        # listed words (Te Reo place names) get correct phonemic pronunciation.
        self.pronunciation_dict_id = pronunciation_dictionary_id
        self.pronunciation_dict_version_id = pronunciation_dictionary_version_id
        # Generous read timeout — first byte from ElevenLabs is usually <1s
        # but can spike on cold paths.
        self._timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)

    async def open_stream(self, text: str) -> tuple[httpx.AsyncClient, httpx.Response]:
        """Open a streaming TTS request and validate the upstream status.

        On success returns ``(client, response)`` — both are open and the
        caller is responsible for closing them. Use :meth:`stream_chunks` to
        iterate the body and close cleanly when done.

        On ElevenLabs 4xx/5xx, raises :class:`ElevenLabsError` with the
        parsed status + message. The caller can surface a clean error to
        the user before any response bytes have been sent.
        """
        url = f"{ELEVENLABS_BASE}/text-to-speech/{self.voice_id}/stream"
        headers = {
            "xi-api-key": self.api_key,
            "accept": "audio/mpeg",
            "content-type": "application/json",
        }
        body: dict = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": self.stability,
                "similarity_boost": self.similarity_boost,
                "style": self.style,
                "use_speaker_boost": True,
            },
        }
        if self.pronunciation_dict_id and self.pronunciation_dict_version_id:
            body["pronunciation_dictionary_locators"] = [
                {
                    "pronunciation_dictionary_id": self.pronunciation_dict_id,
                    "version_id": self.pronunciation_dict_version_id,
                }
            ]

        client = httpx.AsyncClient(timeout=self._timeout)
        try:
            request = client.build_request("POST", url, headers=headers, json=body)
            response = await client.send(request, stream=True)
        except Exception:
            await client.aclose()
            raise

        if response.status_code >= 400:
            err_body = b""
            try:
                err_body = await response.aread()
            finally:
                await response.aclose()
                await client.aclose()
            log.error(
                "ElevenLabs error %s: %s", response.status_code, err_body[:500]
            )
            raise _parse_error(response.status_code, err_body)

        return client, response

    @staticmethod
    async def stream_chunks(
        client: httpx.AsyncClient, response: httpx.Response
    ) -> AsyncIterator[bytes]:
        """Yield MP3 chunks from an open response, then close both resources."""
        try:
            async for chunk in response.aiter_bytes(chunk_size=4096):
                if chunk:
                    yield chunk
        finally:
            await response.aclose()
            await client.aclose()
