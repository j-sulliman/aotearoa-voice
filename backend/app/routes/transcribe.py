"""POST /api/transcribe — audio blob in, text out.

Catches the OpenAI SDK's structured exceptions and converts them into clean
HTTPExceptions with a ``detail`` payload the frontend can render in the
transcript pane. Mirrors the synthesise route's error-handling shape.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    PermissionDeniedError,
    RateLimitError,
)

log = logging.getLogger(__name__)

router = APIRouter()

MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB — generous for ~5 min of webm audio
ALLOWED_PREFIXES = ("audio/",)


def _detail(kind: str, message: str) -> dict:
    return {"kind": kind, "message": message}


@router.post("/api/transcribe")
async def transcribe(request: Request, file: UploadFile = File(...)) -> dict:
    if file.content_type and not file.content_type.startswith(ALLOWED_PREFIXES):
        raise HTTPException(
            status_code=415,
            detail=_detail("unsupported_media", f"Unsupported content_type: {file.content_type}"),
        )

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(
            status_code=400,
            detail=_detail("empty_audio", "Empty audio upload — hold the button while you speak."),
        )
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=413,
            detail=_detail("audio_too_large", "Audio file too large."),
        )

    whisper = request.app.state.whisper
    log.info(
        "Transcribing %d bytes (filename=%s, content_type=%s)",
        len(audio_bytes),
        file.filename,
        file.content_type,
    )

    try:
        text = await whisper.transcribe(audio_bytes, filename=file.filename or "audio.webm")
    except BadRequestError as e:
        # Most common case: a brief tap produced a malformed/empty webm or mp4
        # (Safari without timeslice, very short press, etc.). The data is
        # client-side bad rather than a server problem — return 400 so it
        # flows through Cloudflare unchanged with our CORS headers + JSON.
        log.warning("Whisper rejected audio: %s", e)
        raise HTTPException(
            status_code=400,
            detail=_detail(
                "invalid_audio",
                "The recording came through too short or malformed for the "
                "speech service to read. Hold the microphone for at least a "
                "second and try again.",
            ),
        ) from e
    except AuthenticationError as e:
        raise HTTPException(
            status_code=502,
            detail=_detail(
                "invalid_api_key",
                "Speech-to-text service is misconfigured (invalid credentials). "
                "Please contact the demo owner.",
            ),
        ) from e
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=502,
            detail=_detail(
                "missing_permissions",
                "Speech-to-text service is misconfigured (missing permissions). "
                "Please contact the demo owner.",
            ),
        ) from e
    except RateLimitError as e:
        raise HTTPException(
            status_code=503,
            detail=_detail(
                "rate_limited",
                "Speech-to-text service is rate-limiting us — please try again in a moment.",
            ),
        ) from e
    except (APIConnectionError, APITimeoutError) as e:
        raise HTTPException(
            status_code=503,
            detail=_detail(
                "stt_unavailable",
                "Couldn't reach the speech-to-text service — please try again.",
            ),
        ) from e
    except APIError as e:
        log.exception("Whisper API error")
        raise HTTPException(
            status_code=502,
            detail=_detail(
                "stt_error",
                "Speech-to-text service hit an error. Please try again in a moment.",
            ),
        ) from e

    log.info("Transcribed -> %d chars", len(text))
    return {"text": text}
