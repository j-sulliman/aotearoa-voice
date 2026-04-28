"""POST /api/chat — run the Claude + MCP agent loop, return reply + traces.

The backend is stateless: the client passes the full conversation history
in each request. This keeps deployment trivial (no session store) and makes
the API trivial to test with curl.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..agent.claude_client import run_agent
from ..agent.mcp_client import open_mcp_session
from ..limits import RATE_LIMIT, limiter

log = logging.getLogger(__name__)

router = APIRouter()


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1)


class ToolCallView(BaseModel):
    name: str
    input: dict[str, Any]
    result_preview: str


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[ToolCallView]
    iterations: int


def _to_anthropic_messages(messages: list[ChatMessage]) -> list[dict[str, Any]]:
    """Convert the simple client-side {role, content} schema into Anthropic
    Messages format. Content is wrapped in a single text block."""
    return [{"role": m.role, "content": m.content} for m in messages]


@router.post("/api/chat", response_model=ChatResponse)
@limiter.limit(RATE_LIMIT)
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    state = request.app.state
    if body.messages[-1].role != "user":
        raise HTTPException(status_code=400, detail="Final message must be from the user.")

    try:
        tool_defs = await state.tool_def_cache.get()
    except Exception as e:
        log.exception("Failed to load MCP tool defs")
        raise HTTPException(
            status_code=503,
            detail=f"MCP server unavailable: {e}",
        ) from e

    try:
        async with open_mcp_session(state.settings.mcp_server_url) as mcp_session:
            agent_response = await run_agent(
                client=state.anthropic,
                model=state.settings.anthropic_model,
                messages=_to_anthropic_messages(body.messages),
                tool_defs=tool_defs,
                mcp_session=mcp_session,
            )
    except Exception as e:
        log.exception("Agent loop failed")
        # The MCP server might have restarted — invalidate the cache so the
        # next request picks up fresh tool defs.
        state.tool_def_cache.invalidate()
        raise HTTPException(status_code=502, detail=f"Agent error: {e}") from e

    return ChatResponse(
        reply=agent_response.reply,
        tool_calls=[ToolCallView(**t.to_dict()) for t in agent_response.tool_calls],
        iterations=agent_response.iterations,
    )
