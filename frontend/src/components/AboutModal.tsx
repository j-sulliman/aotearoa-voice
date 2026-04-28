interface AboutModalProps {
  onClose: () => void;
}

export function AboutModal({ onClose }: AboutModalProps) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
        <div className="modal-head">
          <span className="mono dim">— HOW IT'S BUILT</span>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        <h2 className="modal-title">Voice → text → tools → text → voice.</h2>
        <div className="arch">
          <ArchBlock label="Microphone" sub="MediaRecorder · webm/opus" />
          <ArchArrow note="POST /api/transcribe" />
          <ArchBlock label="Transcribe" sub="OpenAI Whisper" />
          <ArchArrow note="POST /api/chat" />
          <ArchBlock label="Agent" sub="Claude · MCP tools" />
          <ArchArrow note="POST /api/synthesise" />
          <ArchBlock label="Synthesise" sub="ElevenLabs · streamed" />
          <ArchArrow note="audio/mpeg" />
          <ArchBlock label="Speaker" sub="<audio> playback" highlight />
        </div>
        <p className="modal-note">
          Tools the agent can call: <span className="mono">find_locations</span>,
          <span className="mono"> get_location_detail</span>,
          <span className="mono"> get_weather</span>,
          <span className="mono"> get_pronunciation_guide</span>,
          <span className="mono"> find_nearby</span>. Each call is surfaced live in the
          Behind&nbsp;the&nbsp;scenes panel, with the same MCP server reachable directly at{" "}
          <span className="mono">/sse</span> from any MCP client.
        </p>
      </div>
    </div>
  );
}

function ArchBlock({ label, sub, highlight }: { label: string; sub: string; highlight?: boolean }) {
  return (
    <div className={`arch-block ${highlight ? "arch-block--hi" : ""}`}>
      <div className="arch-label">{label}</div>
      <div className="arch-sub mono">{sub}</div>
    </div>
  );
}

function ArchArrow({ note }: { note: string }) {
  return (
    <div className="arch-arrow">
      <div className="arch-arrow-line" />
      <div className="arch-arrow-note mono">{note}</div>
    </div>
  );
}
