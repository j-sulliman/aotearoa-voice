import type { ToolCall } from "../lib/api";

interface ToolCallPanelProps {
  toolCalls: ToolCall[];
  iterations: number;
  open: boolean;
  onToggle: () => void;
}

export function ToolCallPanel({ toolCalls, iterations, open, onToggle }: ToolCallPanelProps) {
  return (
    <div className={`tool-panel ${open ? "tool-panel--open" : ""}`}>
      <button className="tool-panel-header" onClick={onToggle} aria-expanded={open}>
        <div className="tool-panel-title">
          <span className="tool-panel-eyebrow mono">— BEHIND THE SCENES</span>
          <span className="tool-panel-summary">
            {toolCalls.length} tool {toolCalls.length === 1 ? "call" : "calls"}
            {iterations ? <span className="dim"> · {iterations} iter.</span> : null}
          </span>
        </div>
        <span className={`tool-panel-chev ${open ? "open" : ""}`}>›</span>
      </button>
      {open && (
        <div className="tool-panel-body">
          {toolCalls.length === 0 ? (
            <div className="tool-empty">No tool calls yet.</div>
          ) : (
            toolCalls.map((tc, i) => <ToolCallView key={i} tc={tc} />)
          )}
        </div>
      )}
    </div>
  );
}

function ToolCallView({ tc }: { tc: ToolCall }) {
  return (
    <div className="tool-call">
      <div className="tool-call-row">
        <span className="tool-call-arrow">→</span>
        <span className="tool-call-name mono">{tc.name}</span>
        <span className="tool-call-input mono">({fmtInput(tc.input)})</span>
      </div>
      <div className="tool-call-result mono" title={tc.result_preview}>
        {tc.result_preview}
      </div>
    </div>
  );
}

function fmtInput(input: Record<string, unknown> | undefined): string {
  if (!input) return "";
  return Object.entries(input)
    .map(([k, v]) => `${k}: ${typeof v === "string" ? `"${v}"` : JSON.stringify(v)}`)
    .join(", ");
}
