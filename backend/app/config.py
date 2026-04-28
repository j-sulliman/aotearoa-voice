"""Centralised settings for the Aotearoa Voice backend.

Reads from environment. We avoid pydantic-settings to keep the dependency
surface small — every var has a clear default or a fail-fast accessor.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # Anthropic
    anthropic_api_key: str
    anthropic_model: str

    # OpenAI Whisper
    openai_api_key: str
    whisper_model: str

    # ElevenLabs
    elevenlabs_api_key: str
    elevenlabs_voice_id: str
    elevenlabs_model_id: str
    elevenlabs_stability: float
    elevenlabs_similarity_boost: float
    elevenlabs_style: float
    # Optional pronunciation dictionary (improves Te Reo Māori place-name
    # pronunciation). Both must be set for the dictionary to take effect;
    # leave blank to use the model's default pronunciation.
    elevenlabs_pronunciation_dict_id: str | None
    elevenlabs_pronunciation_dict_version_id: str | None

    # MCP
    mcp_server_url: str

    # Server
    allowed_origins: list[str]
    rate_limit_per_minute: int
    log_level: str


def _require(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(
            f"Required environment variable {name} is not set. "
            f"See .env.example."
        )
    return val


def load_settings() -> Settings:
    origins_raw = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
    origins = [o.strip() for o in origins_raw.split(",") if o.strip()]

    return Settings(
        anthropic_api_key=_require("ANTHROPIC_API_KEY"),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        openai_api_key=_require("OPENAI_API_KEY"),
        whisper_model=os.getenv("WHISPER_MODEL", "whisper-1"),
        elevenlabs_api_key=_require("ELEVENLABS_API_KEY"),
        elevenlabs_voice_id=_require("ELEVENLABS_VOICE_ID"),
        elevenlabs_model_id=os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2"),
        elevenlabs_stability=float(os.getenv("ELEVENLABS_STABILITY", "0.5")),
        elevenlabs_similarity_boost=float(os.getenv("ELEVENLABS_SIMILARITY_BOOST", "0.75")),
        elevenlabs_style=float(os.getenv("ELEVENLABS_STYLE", "0.2")),
        elevenlabs_pronunciation_dict_id=os.getenv("ELEVENLABS_PRONUNCIATION_DICTIONARY_ID") or None,
        elevenlabs_pronunciation_dict_version_id=os.getenv("ELEVENLABS_PRONUNCIATION_DICTIONARY_VERSION_ID") or None,
        mcp_server_url=os.getenv("MCP_SERVER_URL", "http://mcp_server:8001/sse"),
        allowed_origins=origins,
        rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "20")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
