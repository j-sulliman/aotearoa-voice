"""Claude orchestration loop — runs Anthropic Messages with MCP tool calling.

The loop is bounded (max 5 iterations) to keep demo turns predictable. Tool
calls are dispatched against the MCP session passed in by the route, so the
same session services every tool call within a single user turn.

Prompt caching is enabled on the system prompt and tool definitions —
within a 5-minute window the cache hit covers ~80% of input tokens, which
materially improves both latency and cost on repeat turns.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from anthropic import AsyncAnthropic

from .mcp_client import MCPSession
from .system_prompt import SYSTEM_PROMPT

log = logging.getLogger(__name__)

MAX_AGENT_ITERATIONS = 5
MAX_OUTPUT_TOKENS = 600  # ~3 short sentences of speech, well within the budget.


@dataclass
class ToolCallTrace:
    """One tool call as it appeared in the agent loop. Surfaced to the
    frontend's optional 'behind the scenes' panel."""

    name: str
    input: dict[str, Any]
    result_preview: str  # truncated for UI display

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "input": self.input, "result_preview": self.result_preview}


@dataclass
class AgentResponse:
    reply: str
    tool_calls: list[ToolCallTrace]
    iterations: int


def _truncate(s: str, n: int = 4000) -> str:
    # Generous cap — large enough for any of our tools' full JSON output (so
    # the frontend can JSON.parse it to extract location IDs), small enough
    # to bound a runaway tool result. The UI can re-truncate for display.
    return s if len(s) <= n else s[: n - 1] + "…"


async def run_agent(
    *,
    client: AsyncAnthropic,
    model: str,
    messages: list[dict[str, Any]],
    tool_defs: list[dict],
    mcp_session: MCPSession,
) -> AgentResponse:
    """Run the Claude + MCP tool loop until the model emits an end_turn.

    ``messages`` is the running conversation in Anthropic format. We mutate
    a local copy so we don't surprise the caller.
    """
    convo: list[dict[str, Any]] = list(messages)
    traces: list[ToolCallTrace] = []

    # Cache the system prompt and tool defs — both stable across requests.
    system_blocks = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }
    ]
    cached_tools = list(tool_defs)
    if cached_tools:
        # Marking the last tool def with cache_control caches the whole tools
        # array — that's how the Anthropic prompt-cache breakpoint works.
        cached_tools[-1] = {**cached_tools[-1], "cache_control": {"type": "ephemeral"}}

    for iteration in range(1, MAX_AGENT_ITERATIONS + 1):
        response = await client.messages.create(
            model=model,
            max_tokens=MAX_OUTPUT_TOKENS,
            system=system_blocks,
            tools=cached_tools,
            messages=convo,
        )

        if response.stop_reason != "tool_use":
            text = "".join(
                getattr(b, "text", "") for b in response.content if b.type == "text"
            ).strip()
            log.info(
                "Agent finished after %d iteration(s); stop_reason=%s; tool_calls=%d",
                iteration,
                response.stop_reason,
                len(traces),
            )
            return AgentResponse(reply=text, tool_calls=traces, iterations=iteration)

        # Append the assistant turn (containing tool_use blocks) to the convo,
        # then dispatch each tool call and append a single user turn carrying
        # all the tool_results.
        convo.append({"role": "assistant", "content": [b.model_dump() for b in response.content]})

        tool_results: list[dict[str, Any]] = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            log.info("Calling MCP tool %s with %s", block.name, block.input)
            result_str = await mcp_session.call_tool(block.name, dict(block.input))
            traces.append(
                ToolCallTrace(
                    name=block.name,
                    input=dict(block.input),
                    result_preview=_truncate(result_str),
                )
            )
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_str,
                }
            )

        convo.append({"role": "user", "content": tool_results})

    # Hit the iteration ceiling — return whatever text we have, plus a note.
    log.warning("Agent hit MAX_AGENT_ITERATIONS=%d", MAX_AGENT_ITERATIONS)
    return AgentResponse(
        reply=(
            "I'm having trouble pulling that together right now — "
            "want to try a more specific question?"
        ),
        tool_calls=traces,
        iterations=MAX_AGENT_ITERATIONS,
    )
