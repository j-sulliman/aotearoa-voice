import { useEffect, useState } from "react";

interface WaveformProps {
  level?: number;
  bars?: number;
  color?: string;
  speaking?: boolean;
}

/**
 * Simple animated waveform — `level` (0–1) drives amplitude, `tick` adds
 * cross-bar phase variety. Same shape the design specified.
 */
export function Waveform({ level = 0, bars = 9, color = "#f4f1ec", speaking = false }: WaveformProps) {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let raf = 0;
    const loop = () => {
      setTick((t) => t + 1);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, []);

  const t = tick * 0.12;
  const amp = level * 100; // level is 0–1 from RMS
  return (
    <div className="waveform">
      {Array.from({ length: bars }).map((_, i) => {
        const phase = i * 0.7 + t;
        const wave = Math.abs(Math.sin(phase)) * 0.5 + Math.abs(Math.sin(phase * 1.7 + i)) * 0.5;
        const h = 6 + wave * (amp + (speaking ? 18 : 22));
        return (
          <span
            key={i}
            className="wave-bar"
            style={{ height: `${h}px`, background: color, opacity: 0.65 + wave * 0.35 }}
          />
        );
      })}
    </div>
  );
}
