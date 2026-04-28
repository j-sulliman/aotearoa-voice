import { useEffect, useRef } from "react";

export type TurnRole = "user" | "assistant" | "error";

export interface Turn {
  role: TurnRole;
  content: string;
  time: string;
}

interface TranscriptPaneProps {
  turns: Turn[];
  activeAssistantText: string;
  isProcessing: boolean;
}

export function TranscriptPane({ turns, activeAssistantText, isProcessing }: TranscriptPaneProps) {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [turns, activeAssistantText, isProcessing]);

  return (
    <div className="transcript" ref={ref}>
      {turns.length === 0 && !isProcessing && !activeAssistantText && (
        <div className="transcript-empty">
          <span className="empty-eyebrow mono">— TRANSCRIPT</span>
          <p>Hold the microphone and ask about anywhere in Aotearoa.</p>
        </div>
      )}
      {turns.map((t, i) => (
        <TurnBlock key={i} turn={t} />
      ))}
      {isProcessing && (
        <div className="turn turn--assistant">
          <div className="turn-meta">
            <span className="turn-role">GUIDE</span>
            <span className="turn-time">— now</span>
          </div>
          <div className="turn-text turn-text--thinking">
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
          </div>
        </div>
      )}
      {activeAssistantText && (
        <div className="turn turn--assistant turn--live">
          <div className="turn-meta">
            <span className="turn-role">GUIDE</span>
            <span className="turn-time">— speaking</span>
          </div>
          <div className="turn-text">
            {activeAssistantText}
            <span className="caret" />
          </div>
        </div>
      )}
    </div>
  );
}

function TurnBlock({ turn }: { turn: Turn }) {
  const role = turn.role === "user" ? "YOU" : turn.role === "error" ? "ERROR" : "GUIDE";
  return (
    <div className={`turn turn--${turn.role}`}>
      <div className="turn-meta">
        <span className="turn-role">{role}</span>
        <span className="turn-time">— {turn.time}</span>
      </div>
      <div className="turn-text">{turn.content}</div>
    </div>
  );
}
