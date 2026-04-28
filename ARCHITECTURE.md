# Architecture

A deeper walk through the moving parts of Aotearoa Voice. The README has the why; this document has the how.

## The conversational loop

A single user turn is six hops:

```
1. Browser captures audio (Web Audio API, webm/opus, 16 kHz mono)
2. POST /api/transcribe   → backend → OpenAI Whisper → text
3. POST /api/chat         → backend → Claude + MCP tool loop → reply text + tool traces
4. POST /api/synthesise   → backend → ElevenLabs streaming → audio/mpeg
5. Browser streams audio playback (starts on first chunk, doesn't wait)
6. Map view pans/zooms if the agent referenced a known location
```

The backend is **stateless** — every request carries the full conversation history. This makes deployment trivial and makes the API trivial to test:

```bash
curl http://localhost:8002/api/chat \
  -H 'content-type: application/json' \
  -d '{"messages":[{"role":"user","content":"Tell me about Wai-O-Tapu."}]}'
```

## Latency budget

End-to-end target: **under 4 seconds** from end-of-user-speech to start-of-agent-speech.

| Stage | Budget | Notes |
| --- | ---: | --- |
| Transcribe (Whisper) | < 800ms | 5–10s clips, OpenAI us-east latency |
| Claude + MCP tool loop | < 2s | 1 tool call typical, prompt cache covers repeat turns |
| ElevenLabs first byte | < 1s | streaming endpoint — playback starts here |
| Network + frontend | < 200ms | Cloudflare Tunnel adds ~50ms |

If any stage blows its budget, the README's "Production considerations" section is where I'd document it.

## Backend (FastAPI)

Composition root: [`backend/app/main.py`](backend/app/main.py). At startup:

1. `load_settings()` validates required env vars (fail-fast if any are missing).
2. The Anthropic, Whisper, and ElevenLabs clients are constructed once and stored on `app.state`.
3. A lazy `ToolDefCache` is created — it lists tools from the MCP server on first `/api/chat` request and caches them.
4. Routes are mounted; CORS and per-IP rate limiting are configured.

Routes:

- `POST /api/transcribe` — multipart audio in, `{text}` out. See [`routes/transcribe.py`](backend/app/routes/transcribe.py).
- `POST /api/chat` — `{messages: [{role, content}]}` in, `{reply, tool_calls, iterations}` out. See [`routes/chat.py`](backend/app/routes/chat.py).
- `POST /api/synthesise` — `{text}` in, `audio/mpeg` stream out. See [`routes/synthesise.py`](backend/app/routes/synthesise.py).
- `GET /healthz` — liveness probe for Cloudflare Tunnel and docker-compose.

## The agent loop

[`backend/app/agent/claude_client.py`](backend/app/agent/claude_client.py) implements a bounded tool-calling loop:

1. Build the running message list and call `anthropic.messages.create(...)` with the system prompt, MCP tools, and conversation.
2. If `stop_reason == "tool_use"`, dispatch each tool call against the live MCP session, append the assistant turn (with `tool_use` blocks) plus a synthetic user turn (with `tool_result` blocks), and loop.
3. Otherwise, return the concatenated text content.
4. Cap at `MAX_AGENT_ITERATIONS = 5` to prevent runaway. Cap output at 600 tokens — well past 3 short sentences, but a hard ceiling.

**Prompt caching.** Both the system prompt and the tools array carry `cache_control: {type: "ephemeral"}` breakpoints. Within a 5-minute window the cache hit covers the vast majority of input tokens — a meaningful latency and cost win on repeat turns.

**MCP session lifecycle.** One SSE session per `/api/chat` request, used for all tool calls in that request's loop. Cheaper than re-handshaking per tool call, simpler than maintaining a long-lived session pool. See [`agent/mcp_client.py`](backend/app/agent/mcp_client.py).

## MCP server

[`mcp_server/server.py`](mcp_server/server.py) uses Anthropic's `FastMCP` SDK with SSE transport, mounted on a Starlette app so we can serve `/healthz` alongside the SSE routes (`/sse` and `/messages/`).

The five tools each live in their own module under [`mcp_server/tools/`](mcp_server/tools/) and are pure functions over in-memory data loaded from JSON at startup. No database — the dataset is 22 locations (8 hand-curated demo destinations plus 14 major cities and regions including Wellington, Queenstown, Christchurch, Dunedin, Napier and Nelson) and a pronunciation table.

The tools are designed to compose:

- *Single-tool:* `"Tell me about Wai-O-Tapu"` → `get_location_detail` → narrate.
- *Chained:* `"What's the weather like in Queenstown?"` → `find_locations(region="Queenstown")` → `get_weather(location_id=...)` → narrate.
- *Discovery:* `"What should I do near Rotorua?"` → `find_locations(region="Rotorua")` → `find_nearby(location_id=..., category="walks")` → narrate options.

## Voice strategy

- **Voice:** Jamie's cloned voice, created in ElevenLabs ahead of time. The voice ID is supplied via `ELEVENLABS_VOICE_ID`.
- **Model:** `eleven_multilingual_v2`. Best handling of Te Reo proper nouns within an English voice.
- **Settings:** stability 0.5, similarity boost 0.75, style 0.2. Tuned during build to keep the narration warm without drift.
- **Pronunciation dictionary:** an ElevenLabs PLS dictionary at [`scripts/pronunciations.pls`](scripts/pronunciations.pls) gives IPA transcriptions for ~20 Te Reo place names, iwi, and greetings. The backend includes the dictionary's locator in every TTS request via `pronunciation_dictionary_locators`, so listed words are pronounced according to the dictionary rather than the model's default. Set up once via [`scripts/setup_pronunciation_dict.py`](scripts/setup_pronunciation_dict.py); the resulting `dictionary_id` and `version_id` go into `.env`. Optional — TTS works without it, just with worse Te Reo fidelity.
- **Streaming:** [`voice/elevenlabs_client.py`](backend/app/voice/elevenlabs_client.py) calls the streaming endpoint and yields MP3 chunks straight to a FastAPI `StreamingResponse`. Playback starts on the first chunk, not after full synthesis.

## Cultural handling

Pronunciation handling is not improvised. Every Te Reo place name we voice has a verified entry in [`mcp_server/data/pronunciations.json`](mcp_server/data/pronunciations.json) — phonetic, audio hint, and meaning. The system prompt instructs the agent to use the English form when in doubt rather than guess.

Locations are well-known public attractions, descriptions stay at tourist-information depth, and the agent is explicitly instructed to redirect questions about iwi, marae, and tikanga to local sources.

## Deployment

**Primary:** local Docker Compose on a workstation, exposed via Cloudflare Tunnel. See [`deploy/cloudflared.config.yml`](deploy/cloudflared.config.yml) for a reference tunnel config.

**Alternative:** [`deploy/cloud-run/`](deploy/cloud-run/) ships a `deploy.sh` that stands the same three images up as managed Cloud Run services. The MCP server can also run standalone (e.g. behind a public hostname) if you'd rather host the tools centrally and let multiple agents call into it — `deploy.sh` deploys it as `--allow-unauthenticated` so Claude Desktop can also point at the same endpoint.

## Frontend API contract

The frontend (built separately in Claude Design) talks to three endpoints:

```
POST /api/transcribe
  multipart/form-data: file=<audio blob>
  ->  {"text": "..."}

POST /api/chat
  application/json: {"messages": [{"role": "user"|"assistant", "content": "..."}, ...]}
  ->  {"reply": "...", "tool_calls": [{"name", "input", "result_preview"}], "iterations": N}

POST /api/synthesise
  application/json: {"text": "..."}
  ->  audio/mpeg stream
```

All endpoints accept and return UTF-8 with macron-aware text. The `tool_calls` array is what the optional "behind the scenes" panel renders — name, input, and a truncated preview of the result.
