// Backend API wrapper. Three endpoints:
//   POST /api/transcribe — multipart audio in, { text } out
//   POST /api/chat       — { messages } in, { reply, tool_calls, iterations } out
//   POST /api/synthesise — { text } in, audio/mpeg stream out

import { isLocationId, type LocationId } from "./locations";

const BASE: string = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8002").replace(/\/$/, "");

export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export interface ToolCall {
  name: string;
  input: Record<string, unknown>;
  result_preview: string;
}

export interface ChatResponse {
  reply: string;
  tool_calls: ToolCall[];
  iterations: number;
}

export interface TranscribeResponse {
  text: string;
}

/**
 * Thrown for any non-2xx response from the backend. ``detail`` holds the
 * user-facing message extracted from the response body (the backend wraps
 * upstream provider errors into ``{detail: {kind, message}}``).
 */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
    public readonly kind?: string,
  ) {
    super(`${status}: ${detail}`);
    this.name = "ApiError";
  }
}

async function _readError(res: Response): Promise<{ detail: string; kind?: string }> {
  try {
    const data = await res.json();
    if (typeof data === "object" && data && "detail" in data) {
      const detail = (data as { detail: unknown }).detail;
      if (typeof detail === "string") return { detail };
      if (detail && typeof detail === "object") {
        const obj = detail as { message?: unknown; kind?: unknown };
        const message =
          typeof obj.message === "string" ? obj.message : JSON.stringify(detail);
        const kind = typeof obj.kind === "string" ? obj.kind : undefined;
        return { detail: message, kind };
      }
      return { detail: JSON.stringify(detail) };
    }
    return { detail: JSON.stringify(data) };
  } catch {
    return { detail: res.statusText || `HTTP ${res.status}` };
  }
}

async function _throwError(res: Response): Promise<never> {
  const { detail, kind } = await _readError(res);
  throw new ApiError(res.status, detail, kind);
}

export async function healthz(signal?: AbortSignal): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/healthz`, { signal });
    return res.ok;
  } catch {
    return false;
  }
}

export async function transcribe(audio: Blob, signal?: AbortSignal): Promise<string> {
  const fd = new FormData();
  // The backend sniffs filename to detect MIME type. webm covers the
  // browser's MediaRecorder default; if the blob has a different type, use
  // its extension hint.
  const ext = audio.type.includes("ogg")
    ? "ogg"
    : audio.type.includes("mp4")
      ? "mp4"
      : audio.type.includes("wav")
        ? "wav"
        : "webm";
  // Diagnostic: log the blob shape on each upload. If transcription starts
  // failing intermittently, this is the first place to look — Safari is
  // notorious for producing tiny / malformed blobs on quick stops.
  // eslint-disable-next-line no-console
  console.log("[aotearoa] transcribe upload", {
    type: audio.type,
    size: audio.size,
    ext,
  });
  fd.append("file", audio, `audio.${ext}`);
  const res = await fetch(`${BASE}/api/transcribe`, {
    method: "POST",
    body: fd,
    signal,
  });
  if (!res.ok) await _throwError(res);
  const data = (await res.json()) as TranscribeResponse;
  return data.text ?? "";
}

export async function chat(messages: ChatMessage[], signal?: AbortSignal): Promise<ChatResponse> {
  const res = await fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ messages }),
    signal,
  });
  if (!res.ok) await _throwError(res);
  return (await res.json()) as ChatResponse;
}

export async function synthesise(text: string, signal?: AbortSignal): Promise<Blob> {
  // ElevenLabs streams audio/mpeg. Reading to a Blob waits for full body
  // before playback, costing ~1–2s versus MSE streaming. For demo lengths
  // (<30s of audio) the simplicity is worth it; revisit with MSE if the
  // latency budget gets tight.
  const res = await fetch(`${BASE}/api/synthesise`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ text }),
    signal,
  });
  if (!res.ok) await _throwError(res);
  return await res.blob();
}

// === Tool call inspection helpers ===

/**
 * Extract every location ID a tool call touched — either via `input.location_id`
 * (works for get_location_detail / get_weather / find_nearby) or by JSON-parsing
 * `result_preview` (works for find_locations when the result fit under the
 * backend's truncation cap).
 */
export function extractLocationIds(toolCalls: ToolCall[]): LocationId[] {
  const ids = new Set<LocationId>();
  for (const tc of toolCalls) {
    const inputId = tc.input?.location_id;
    if (typeof inputId === "string" && isLocationId(inputId)) {
      ids.add(inputId);
    }
    const parsed = tryParseJson(tc.result_preview);
    if (Array.isArray(parsed)) {
      for (const item of parsed) {
        if (item && typeof item === "object" && "id" in item) {
          const id = String((item as { id: unknown }).id);
          if (isLocationId(id)) ids.add(id);
        }
      }
    } else if (parsed && typeof parsed === "object" && "id" in parsed) {
      const id = String((parsed as { id: unknown }).id);
      if (isLocationId(id)) ids.add(id);
    }
  }
  return [...ids];
}

function tryParseJson(s: string): unknown {
  if (!s) return null;
  // Strip a trailing ellipsis (the backend's truncation marker) — the parse
  // will still fail on truncated objects, but harmless on complete ones.
  const cleaned = s.endsWith("…") ? s.slice(0, -1) : s;
  try {
    return JSON.parse(cleaned);
  } catch {
    return null;
  }
}
