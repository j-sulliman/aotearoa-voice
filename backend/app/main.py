"""FastAPI entry point for the Aotearoa Voice backend.

Composition root: load settings, wire clients, mount routes, configure CORS
and rate limiting. Every external client lives on ``app.state`` so routes
can reach them via the request object — no module-level singletons.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from anthropic import AsyncAnthropic
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from .agent.mcp_client import ToolDefCache
from .config import load_settings
from .limits import limiter
from .routes import chat as chat_route
from .routes import synthesise as synthesise_route
from .routes import transcribe as transcribe_route
from .stt.whisper_client import WhisperClient
from .voice.elevenlabs_client import ElevenLabsClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
    )
    log = logging.getLogger("aotearoa")
    log.info("Starting backend (model=%s)", settings.anthropic_model)

    app.state.settings = settings
    app.state.anthropic = AsyncAnthropic(api_key=settings.anthropic_api_key)
    app.state.whisper = WhisperClient(
        api_key=settings.openai_api_key, model=settings.whisper_model
    )
    app.state.elevenlabs = ElevenLabsClient(
        api_key=settings.elevenlabs_api_key,
        voice_id=settings.elevenlabs_voice_id,
        model_id=settings.elevenlabs_model_id,
        stability=settings.elevenlabs_stability,
        similarity_boost=settings.elevenlabs_similarity_boost,
        style=settings.elevenlabs_style,
        pronunciation_dictionary_id=settings.elevenlabs_pronunciation_dict_id,
        pronunciation_dictionary_version_id=settings.elevenlabs_pronunciation_dict_version_id,
    )
    if settings.elevenlabs_pronunciation_dict_id:
        log.info(
            "ElevenLabs pronunciation dictionary active: %s",
            settings.elevenlabs_pronunciation_dict_id,
        )
    app.state.tool_def_cache = ToolDefCache(settings.mcp_server_url)

    yield

    log.info("Shutting down backend")


app = FastAPI(
    title="Aotearoa Voice — backend",
    description=(
        "STT + agent + TTS orchestrator for the Aotearoa Voice tour-guide demo. "
        "See the project README for context."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# === Rate limiting === (limiter is also referenced by route decorators)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded — slow down a touch."},
    )


# === CORS ===
# CORS middleware needs origins at construction time. We read directly from
# env (the lifespan still validates other required vars on startup).
_origins = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)

# === Routes ===
app.include_router(transcribe_route.router, tags=["stt"])
app.include_router(chat_route.router, tags=["agent"])
app.include_router(synthesise_route.router, tags=["tts"])


@app.get("/healthz", tags=["meta"])
async def healthz() -> dict:
    return {"ok": True, "service": "aotearoa-backend"}


@app.get("/", tags=["meta"])
async def root() -> dict:
    return {
        "service": "aotearoa-voice-backend",
        "endpoints": ["/api/transcribe", "/api/chat", "/api/synthesise", "/healthz"],
        "docs": "/docs",
    }
