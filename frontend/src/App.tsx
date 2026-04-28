import { useCallback, useEffect, useRef, useState } from "react";

import { AboutModal } from "./components/AboutModal";
import { MapView } from "./components/MapView";
import { ToolCallPanel } from "./components/ToolCallPanel";
import { TranscriptPane, type Turn } from "./components/TranscriptPane";
import { VoiceButton, type VoiceState } from "./components/VoiceButton";
import { useAudioRecording } from "./hooks/useAudioRecording";
import {
  ApiError,
  chat,
  extractLocationIds,
  healthz,
  synthesise,
  transcribe,
  type ChatMessage,
  type ToolCall,
} from "./lib/api";
import { LOCATION_COUNT, type LocationId } from "./lib/locations";

const TYPEWRITER_CHARS_PER_SEC = 13;

// 0.1s of mono 16-bit silence at 44.1kHz, base64-encoded WAV. Used to
// "unlock" the audio element on the first user gesture so subsequent
// programmatic .play() calls survive the round-trip wait without tripping
// the browser's autoplay policy. Safari is the strict one here.
const SILENT_WAV_DATA_URL =
  "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=";

export default function App() {
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [activeAssistant, setActiveAssistant] = useState("");
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [iterations, setIterations] = useState(0);
  const [pinned, setPinned] = useState<LocationId[]>(["tamaki-makaurau"]);
  const [activeLocation, setActiveLocation] = useState<LocationId | null>("tamaki-makaurau");
  const [isPanning, setIsPanning] = useState(false);
  const [toolOpen, setToolOpen] = useState(true);
  const [aboutOpen, setAboutOpen] = useState(false);
  const [connecting, setConnecting] = useState(true);
  const [healthOk, setHealthOk] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const recording = useAudioRecording();

  // We append turns as we go; the chat endpoint wants the full message
  // history every request. messagesRef is the source of truth so we don't
  // race state updates.
  const messagesRef = useRef<ChatMessage[]>([]);

  // Single, long-lived <audio> element. Reusing the same element (and
  // priming it during the user gesture) is what keeps autoplay alive across
  // the multi-second STT + agent + TTS round-trip.
  const audioElRef = useRef<HTMLAudioElement | null>(null);
  const audioPrimedRef = useRef(false);

  // Healthz gate
  useEffect(() => {
    let cancelled = false;
    const ctrl = new AbortController();
    healthz(ctrl.signal).then((ok) => {
      if (cancelled) return;
      setHealthOk(ok);
      // Hold the connecting overlay long enough for the slide animation to feel
      // intentional, but no longer than necessary.
      setTimeout(() => setConnecting(false), 700);
    });
    return () => {
      cancelled = true;
      ctrl.abort();
    };
  }, []);

  const nowLabel = () => {
    const d = new Date();
    return `${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}`;
  };

  /** Push an error turn into the transcript and surface it on the button. */
  const failTurn = useCallback((message: string) => {
    setTurns((prev) => [...prev, { role: "error", content: message, time: nowLabel() }]);
    setErrorMessage(message);
    setVoiceState("error");
    setActiveAssistant("");
    window.setTimeout(() => {
      setVoiceState((s) => (s === "error" ? "idle" : s));
      setErrorMessage(null);
    }, 4000);
  }, []);

  /** Get-or-create the shared audio element. */
  const getAudioEl = useCallback((): HTMLAudioElement => {
    if (!audioElRef.current) {
      const a = new Audio();
      a.preload = "auto";
      audioElRef.current = a;
    }
    return audioElRef.current;
  }, []);

  /**
   * Prime the audio element with silence while we hold a fresh user
   * activation token. After this call succeeds once, subsequent .play()
   * calls on the same element are allowed even after long awaits.
   */
  const primeAudio = useCallback(async () => {
    if (audioPrimedRef.current) return;
    const a = getAudioEl();
    try {
      a.src = SILENT_WAV_DATA_URL;
      await a.play();
      a.pause();
      a.currentTime = 0;
      audioPrimedRef.current = true;
    } catch {
      // Strict autoplay policy — we'll show a soft fallback if real play fails.
    }
  }, [getAudioEl]);

  const handlePressStart = useCallback(async () => {
    setErrorMessage(null);
    // Prime audio FIRST while we still have user activation. Don't await it
    // gating the recording — we want the mic to start immediately.
    void primeAudio();
    await recording.start();
    if (recording.error) {
      failTurn(recording.error);
      return;
    }
    setVoiceState("recording");
  }, [recording, failTurn, primeAudio]);

  const handlePressEnd = useCallback(async () => {
    if (voiceState !== "recording") return;
    setVoiceState("processing");

    let audioBlob: Blob;
    try {
      audioBlob = await recording.stop();
    } catch (e) {
      failTurn(`Couldn't capture audio: ${describe(e)}`);
      return;
    }
    // A truly-empty webm/mp4 blob is a few hundred bytes of header; under that
    // threshold the user almost certainly tapped instead of held. Catch it
    // locally so the user gets a helpful message immediately rather than
    // round-tripping to Whisper for a guaranteed 400.
    if (audioBlob.size < 1024) {
      failTurn("Hold the microphone for at least a second while you speak.");
      return;
    }

    // 1) Transcribe
    let userText: string;
    try {
      userText = (await transcribe(audioBlob)).trim();
    } catch (e) {
      failTurn(apiMessage(e, "Transcription failed"));
      return;
    }
    if (!userText) {
      failTurn("Couldn't make out what you said — try again?");
      return;
    }

    setTurns((prev) => [...prev, { role: "user", content: userText, time: nowLabel() }]);
    const userMsg: ChatMessage = { role: "user", content: userText };
    messagesRef.current = [...messagesRef.current, userMsg];

    // 2) Run the agent
    let chatResp;
    try {
      chatResp = await chat(messagesRef.current);
    } catch (e) {
      failTurn(apiMessage(e, "Agent error"));
      return;
    }

    setToolCalls(chatResp.tool_calls);
    setIterations(chatResp.iterations);

    const newLocations = extractLocationIds(chatResp.tool_calls);
    if (newLocations.length > 0) {
      setPinned((prev) => Array.from(new Set([...prev, ...newLocations])));
      const next = newLocations[0];
      setActiveLocation(next);
      setIsPanning(true);
      window.setTimeout(() => setIsPanning(false), 1300);
    }

    // 3) Synthesise — if this fails (quota, bad key, etc.) we still want to
    // commit the assistant turn so the user can read what was said.
    let blob: Blob | null = null;
    let synthError: string | null = null;
    try {
      blob = await synthesise(chatResp.reply);
    } catch (e) {
      synthError = apiMessage(e, "Voice synthesis failed");
    }

    // Commit the assistant turn regardless of audio success — preserve the
    // reply in the transcript history so it's never lost to a TTS failure.
    const commitAssistant = () => {
      const assistantMsg: ChatMessage = { role: "assistant", content: chatResp.reply };
      messagesRef.current = [...messagesRef.current, assistantMsg];
      setTurns((prev) => [
        ...prev,
        { role: "assistant", content: chatResp.reply, time: nowLabel() },
      ]);
      setActiveAssistant("");
    };

    if (synthError || !blob) {
      commitAssistant();
      failTurn(synthError ?? "Voice synthesis failed.");
      return;
    }

    // 4) Play audio + run typewriter in parallel
    const url = URL.createObjectURL(blob);
    const audio = getAudioEl();
    audio.src = url;

    setVoiceState("speaking");
    const typeoutCtrl = new AbortController();
    const typeoutPromise = typeOut(chatResp.reply, setActiveAssistant, typeoutCtrl.signal);

    let playFailed = false;
    try {
      await audio.play();
    } catch (e) {
      // Autoplay blocked despite priming (very strict environment). Cancel
      // the typewriter and fall through — we'll commit the reply and surface
      // a soft message rather than dropping it.
      typeoutCtrl.abort();
      log("autoplay blocked", e);
      playFailed = true;
    }

    if (!playFailed) {
      await new Promise<void>((resolve) => {
        audio.addEventListener("ended", () => resolve(), { once: true });
        audio.addEventListener("error", () => resolve(), { once: true });
      });
    }
    await typeoutPromise.catch(() => {});
    URL.revokeObjectURL(url);

    commitAssistant();

    if (playFailed) {
      failTurn(
        "The reply is shown above, but your browser blocked audio playback after the wait. " +
          "Hold the mic again to continue — playback usually works on the second try.",
      );
    } else {
      setVoiceState("idle");
    }
  }, [voiceState, recording, failTurn, getAudioEl]);

  // Space-to-talk: hold spacebar to record, release to send. Uses refs to the
  // handlers so the listener is bound once.
  const startRef = useRef(handlePressStart);
  const endRef = useRef(handlePressEnd);
  startRef.current = handlePressStart;
  endRef.current = handlePressEnd;
  const stateRef = useRef(voiceState);
  stateRef.current = voiceState;

  useEffect(() => {
    const isTextField = (el: Element | null) =>
      !!el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || (el as HTMLElement).isContentEditable);
    const onDown = (e: KeyboardEvent) => {
      if (e.code !== "Space" || e.repeat) return;
      if (isTextField(document.activeElement)) return;
      if (stateRef.current !== "idle" && stateRef.current !== "error") return;
      e.preventDefault();
      void startRef.current();
    };
    const onUp = (e: KeyboardEvent) => {
      if (e.code !== "Space") return;
      if (isTextField(document.activeElement)) return;
      if (stateRef.current !== "recording") return;
      e.preventDefault();
      void endRef.current();
    };
    window.addEventListener("keydown", onDown);
    window.addEventListener("keyup", onUp);
    return () => {
      window.removeEventListener("keydown", onDown);
      window.removeEventListener("keyup", onUp);
    };
  }, []);

  return (
    <div className="app">
      {connecting && (
        <div className="connecting">
          <div className="connecting-inner">
            <span className="mono dim">— CONNECTING TO GUIDE</span>
            <div className="connecting-bar">
              <span />
            </div>
          </div>
        </div>
      )}

      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            <span className="brand-dot" />
          </div>
          <div className="brand-text">
            <div className="brand-name">Aotearoa Voice</div>
            <div className="brand-sub mono">A REFERENCE IMPLEMENTATION · ELEVENLABS × MCP</div>
          </div>
        </div>
        <div className="topbar-right">
          <button className="topbar-link" onClick={() => setAboutOpen(true)}>
            How it's built →
          </button>
          <span className="health">
            <span
              className={`health-dot ${connecting ? "" : healthOk ? "ok" : "err"}`}
              aria-hidden
            />
            <span className="mono dim">
              {connecting ? "connecting" : healthOk ? "/healthz · ok" : "/healthz · down"}
            </span>
          </span>
        </div>
      </header>

      <main className="grid">
        <section className="left">
          <div className="hero">
            <div className="eyebrow mono">— A VOICE-DRIVEN GUIDE TO AOTEAROA</div>
            <h1 className="headline">
              Talk to a <span className="ital">Kiwi</span> tour guide.
              <br />
              <span className="dim-headline">Powered by ElevenLabs.</span>
            </h1>
            <p className="sub">
              Ask about places to visit, things to know, where to eat. Built as a reference
              implementation for voice agents over MCP.
            </p>
          </div>

          <div className="voice-section">
            <VoiceButton
              state={voiceState}
              level={recording.level}
              onPressStart={() => void handlePressStart()}
              onPressEnd={() => void handlePressEnd()}
              errorMessage={errorMessage}
            />
            <div className="voice-hint mono dim">
              {voiceState === "idle" && "TAP & HOLD · OR PRESS SPACE"}
              {voiceState === "recording" && "RELEASE TO SEND"}
              {voiceState === "processing" && "TRANSCRIBE · CHAT · SYNTHESISE"}
              {voiceState === "speaking" && "STREAMING AUDIO · MPEG"}
              {voiceState === "error" && "TAP & HOLD TO RETRY"}
            </div>
          </div>

          <TranscriptPane
            turns={turns}
            activeAssistantText={activeAssistant}
            isProcessing={voiceState === "processing"}
          />

          <div className="footer-line mono dim">
            The voice you're hearing is mine, cloned in ElevenLabs.
          </div>
        </section>

        <section className="right">
          <div className="right-eyebrow">
            <span className="mono dim">— AOTEAROA · NEW ZEALAND</span>
            <span className="mono dim">{pinned.length}/{LOCATION_COUNT} PLACES</span>
          </div>
          <div className="map-shell">
            <MapView activeLocation={activeLocation} pinnedIds={pinned} isPanning={isPanning} />
          </div>

          <ToolCallPanel
            toolCalls={toolCalls}
            iterations={iterations}
            open={toolOpen}
            onToggle={() => setToolOpen((o) => !o)}
          />
        </section>
      </main>

      {aboutOpen && <AboutModal onClose={() => setAboutOpen(false)} />}
    </div>
  );
}

function describe(e: unknown): string {
  if (e instanceof Error) return e.message;
  return String(e);
}

/**
 * Pull the user-facing message out of an API failure. ApiError already
 * carries the backend's parsed `detail` (which itself contains the
 * upstream provider's clean message — see backend/app/routes/synthesise.py).
 * For everything else fall back to a generic prefix.
 */
function apiMessage(e: unknown, fallback: string): string {
  if (e instanceof ApiError) return e.detail;
  return `${fallback}: ${describe(e)}`;
}

function log(...args: unknown[]): void {
  // eslint-disable-next-line no-console
  console.warn("[aotearoa]", ...args);
}

/**
 * Type out text at a fixed rate. Approximately matches average TTS speaking
 * pace (~150 wpm); the audio's `ended` event is what actually gates the
 * speaking-state transition, so exact sync isn't required. Cancellable via
 * an AbortSignal so we can stop the typewriter when audio playback fails.
 */
async function typeOut(text: string, setter: (s: string) => void, signal?: AbortSignal): Promise<void> {
  const words = text.split(/(\s+)/);
  const total = text.length;
  const totalMs = (total / TYPEWRITER_CHARS_PER_SEC) * 1000;
  const per = totalMs / Math.max(1, words.length);
  let acc = "";
  for (const w of words) {
    if (signal?.aborted) return;
    acc += w;
    setter(acc);
    await new Promise<void>((r) => window.setTimeout(r, per));
  }
}
