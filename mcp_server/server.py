"""Aotearoa Voice — MCP server (SSE transport).

Exposes five tour-guide tools over the Model Context Protocol. Built with
FastMCP (the official Anthropic Python SDK) and mounted on a Starlette app
so we can serve a ``/healthz`` endpoint alongside the SSE transport.

The SSE endpoint lives at ``/sse``. Pointing Claude Desktop (or any MCP
client) at that URL will let it call the tools directly — same backend, same
data, no demo-frontend required.
"""

from __future__ import annotations

import logging
import os
from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from tools.find_locations import find_locations as _find_locations
from tools.get_location_detail import get_location_detail as _get_location_detail
from tools.get_weather import get_weather as _get_weather
from tools.get_pronunciation_guide import get_pronunciation_guide as _get_pronunciation_guide
from tools.find_nearby import find_nearby as _find_nearby

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("aotearoa-mcp")

# DNS-rebinding guard: the MCP SDK rejects requests whose Host header isn't on
# the whitelist (default: localhost / 127.0.0.1). Inside docker-compose the
# backend reaches us via the service name "mcp_server", and a Cloudflare Tunnel
# adds the public hostname. Override via MCP_ALLOWED_HOSTS (comma-separated)
# for any additional hostnames a deployment exposes us under.
_default_allowed_hosts = ",".join([
    "localhost", "localhost:8001",
    "127.0.0.1", "127.0.0.1:8001",
    "mcp_server", "mcp_server:8001",
])
_allowed_hosts = [
    h.strip()
    for h in os.getenv("MCP_ALLOWED_HOSTS", _default_allowed_hosts).split(",")
    if h.strip()
]

mcp = FastMCP(
    name="aotearoa-tour",
    instructions=(
        "Tools for an Aotearoa New Zealand tour-guide voice agent. "
        "22 curated locations across Aotearoa. Prefer find_locations to discover IDs, "
        "then get_location_detail / get_weather / find_nearby for depth. "
        "Use get_pronunciation_guide before voicing any Te Reo Māori place "
        "name you're unsure about."
    ),
    transport_security=TransportSecuritySettings(allowed_hosts=_allowed_hosts),
)


@mcp.tool()
def find_locations(
    region: str | None = None,
    theme: Literal["nature", "city", "food", "history"] | None = None,
) -> list[dict]:
    """List curated tour locations, optionally filtered by region or theme.

    Args:
        region: Substring match on the region (e.g. "Auckland", "Rotorua").
        theme: One of "nature", "city", "food", "history".
    """
    return _find_locations(region=region, theme=theme)


@mcp.tool()
def get_location_detail(location_id: str) -> dict:
    """Return the full record for a location (description, things to do,
    transit, best season). Use ``find_locations`` to discover IDs."""
    return _get_location_detail(location_id=location_id)


@mcp.tool()
def get_weather(location_id: str) -> dict:
    """Return current conditions and a 3-day outlook for a location.

    This is a demo stub — long-run seasonal averages keyed to the current
    NZ season, not a live forecast.
    """
    return _get_weather(location_id=location_id)


@mcp.tool()
def get_pronunciation_guide(word: str) -> dict:
    """Look up a verified pronunciation for a Te Reo Māori or Aotearoa place
    name. Returns ``error`` if the word isn't in our verified table — we
    don't guess on Te Reo pronunciation.
    """
    return _get_pronunciation_guide(word=word)


@mcp.tool()
def find_nearby(
    location_id: str,
    category: Literal["food", "accommodation", "walks"],
) -> dict:
    """Find nearby food, accommodation, or walks for a location."""
    return _find_nearby(location_id=location_id, category=category)


async def _healthz(_request) -> JSONResponse:
    return JSONResponse({"ok": True, "service": "aotearoa-mcp"})


# FastMCP exposes ``sse_app()`` which is a Starlette app routing /sse and
# /messages/. Mount it under "/" and add /healthz alongside.
app = Starlette(
    routes=[
        Route("/healthz", _healthz),
        Mount("/", app=mcp.sse_app()),
    ]
)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8001"))
    log.info("Starting Aotearoa MCP server on :%s", port)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level=os.getenv("LOG_LEVEL", "info").lower())
