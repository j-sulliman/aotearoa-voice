"""MCP client wrapper for the Aotearoa MCP server.

Pattern: open a fresh SSE session for each /chat request and use it for
all tool calls in that request's agent loop. Tool definitions are cached
on first use and refreshed lazily.

The MCP Python SDK is async-only — we expose an async context manager.
"""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

log = logging.getLogger(__name__)


class MCPSession:
    """Thin wrapper over an initialised :class:`mcp.ClientSession`."""

    def __init__(self, session: ClientSession) -> None:
        self._session = session

    async def list_tool_defs(self) -> list[dict]:
        """Return tools in Anthropic Messages API format."""
        result = await self._session.list_tools()
        return [
            {
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema,
            }
            for tool in result.tools
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Invoke a tool and return its result as a JSON string.

        We always serialise to a string here so the caller can pass it
        straight back to Claude as a ``tool_result`` content block.
        """
        try:
            result = await self._session.call_tool(name, arguments)
        except Exception as e:
            log.exception("MCP tool %s raised", name)
            return json.dumps({"error": f"Tool transport error: {e}"})

        if result.isError:
            return json.dumps({"error": "Tool execution returned an error."})

        # MCP tool results are a list of content blocks. Our tools return
        # JSON-serialisable structures wrapped in a single TextContent. Be
        # defensive in case a tool returns multiple blocks or raw bytes.
        parts: list[str] = []
        for block in result.content:
            text = getattr(block, "text", None)
            if text is not None:
                parts.append(text)
        return "\n".join(parts) if parts else "{}"


@asynccontextmanager
async def open_mcp_session(url: str) -> AsyncIterator[MCPSession]:
    """Open and initialise an MCP SSE session, yielding a usable wrapper."""
    async with sse_client(url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield MCPSession(session)


class ToolDefCache:
    """Lazily cached MCP tool definitions in Anthropic format.

    On first use, opens an MCP session, fetches tool defs, and caches them.
    Set :attr:`stale` to force a refresh (e.g. if the MCP server restarts).
    """

    def __init__(self, url: str) -> None:
        self.url = url
        self._defs: list[dict] | None = None

    @property
    def stale(self) -> bool:
        return self._defs is None

    def invalidate(self) -> None:
        self._defs = None

    async def get(self) -> list[dict]:
        if self._defs is None:
            async with open_mcp_session(self.url) as session:
                self._defs = await session.list_tool_defs()
            log.info("Cached %d MCP tool defs from %s", len(self._defs), self.url)
        return self._defs
