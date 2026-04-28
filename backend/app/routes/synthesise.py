"""POST /api/synthesise — text in, streaming MP3 audio out.

Validates the upstream ElevenLabs response *before* the StreamingResponse
begins, so 4xx/5xx errors come back as proper HTTP errors with a clean
``detail`` payload the frontend can render — instead of a 200 followed by
an aborted stream.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..limits import RATE_LIMIT, limiter
from ..voice.elevenlabs_client import ElevenLabsError

log = logging.getLogger(__name__)

router = APIRouter()

MAX_TEXT_LENGTH = 1500  # ~90s of speech, well past anything the agent should say.


class SynthesiseRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_TEXT_LENGTH)


# Mapping from ElevenLabs' internal status codes to user-facing copy.
# Anything not listed falls through to a generic message keyed off HTTP status.
_USER_MESSAGES: dict[str, str] = {
    "quota_exceeded": (
        "Voice synthesis is temporarily out of credits for this demo. "
        "Please try again later, or let the demo owner know."
    ),
    "invalid_api_key": (
        "Voice service is misconfigured (invalid credentials). "
        "Please contact the demo owner."
    ),
    "missing_permissions": (
        "Voice service is misconfigured (missing permissions on the API key). "
        "Please contact the demo owner."
    ),
    "voice_not_found": (
        "The configured voice can't be found in ElevenLabs. "
        "Please contact the demo owner."
    ),
    "voice_limit_reached": (
        "The ElevenLabs voice library limit has been reached. "
        "Please contact the demo owner."
    ),
}


def _user_message(e: ElevenLabsError) -> str:
    if e.status and e.status in _USER_MESSAGES:
        return _USER_MESSAGES[e.status]
    if e.status_code == 401:
        return (
            "Voice service rejected the request. "
            "Please contact the demo owner."
        )
    if e.status_code == 429:
        return "Voice service is rate-limiting us — please try again in a moment."
    if e.status_code >= 500:
        return "Voice service is unavailable right now — please try again in a moment."
    # Last-resort fallback exposes ElevenLabs' raw message but truncated, so
    # the frontend at least has something specific to render.
    return f"Voice synthesis failed: {e.message[:200]}"


def _http_status_for(e: ElevenLabsError) -> int:
    # Quota exhaustion is "the demo is up but TTS is dry" — 503 (transient
    # service unavailable) reads more accurately to a reviewer than 502
    # (which implies the upstream itself is broken).
    if e.status == "quota_exceeded":
        return 503
    if e.status_code == 429:
        return 503
    return 502


@router.post("/api/synthesise")
@limiter.limit(RATE_LIMIT)
async def synthesise(request: Request, body: SynthesiseRequest) -> StreamingResponse:
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text.")

    elevenlabs = request.app.state.elevenlabs
    log.info("Synthesising %d chars", len(text))

    try:
        client, response = await elevenlabs.open_stream(text)
    except ElevenLabsError as e:
        raise HTTPException(
            status_code=_http_status_for(e),
            detail={
                "kind": e.status or f"http_{e.status_code}",
                "message": _user_message(e),
            },
        ) from e
    except Exception as e:
        log.exception("Failed to open ElevenLabs stream")
        raise HTTPException(
            status_code=502,
            detail={
                "kind": "upstream_error",
                "message": (
                    "Couldn't reach the voice service. "
                    "Please try again in a moment."
                ),
            },
        ) from e

    return StreamingResponse(
        elevenlabs.stream_chunks(client, response),
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "no-store",
            "X-Accel-Buffering": "no",
        },
    )
