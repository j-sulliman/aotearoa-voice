import { Waveform } from "./Waveform";

export type VoiceState = "idle" | "recording" | "processing" | "speaking" | "error";

interface VoiceButtonProps {
  state: VoiceState;
  level: number;
  onPressStart: () => void;
  onPressEnd: () => void;
  errorMessage?: string | null;
}

export function VoiceButton({ state, level, onPressStart, onPressEnd, errorMessage }: VoiceButtonProps) {
  const handleDown = (e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    if (state === "idle" || state === "error") onPressStart();
  };
  const handleUp = (e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    if (state === "recording") onPressEnd();
  };

  return (
    <div className="voice-stage">
      <button
        className={`voice-btn voice-btn--${state}`}
        onMouseDown={handleDown}
        onMouseUp={handleUp}
        onMouseLeave={handleUp}
        onTouchStart={handleDown}
        onTouchEnd={handleUp}
        aria-label={
          state === "recording" ? "Recording — release to send" : "Hold to talk to the tour guide"
        }
      >
        <div className="voice-ring voice-ring--1" />
        <div className="voice-ring voice-ring--2" />
        <div className="voice-ring voice-ring--3" />
        <div className="voice-core">
          {state === "idle" && <MicGlyph />}
          {state === "error" && <MicGlyph />}
          {state === "recording" && <Waveform level={level} bars={9} color="#f4f1ec" />}
          {state === "processing" && <Spinner />}
          {state === "speaking" && <Waveform level={level} bars={9} color="#f4f1ec" speaking />}
        </div>
      </button>
      <div className="voice-label">
        {state === "idle" && (
          <>
            <span className="kbd">HOLD</span> to talk
          </>
        )}
        {state === "recording" && <span className="recording-label">Listening — release to send</span>}
        {state === "processing" && <span>Thinking…</span>}
        {state === "speaking" && <span>Speaking</span>}
        {state === "error" && <span className="error-label">{errorMessage ?? "Try again"}</span>}
      </div>
    </div>
  );
}

function MicGlyph() {
  return (
    <svg width="34" height="34" viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect x="9" y="3" width="6" height="12" rx="3" stroke="#f4f1ec" strokeWidth="1.6" />
      <path
        d="M5 11a7 7 0 0 0 14 0"
        stroke="#f4f1ec"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      <path d="M12 18v3" stroke="#f4f1ec" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function Spinner() {
  return <div className="spinner" />;
}
