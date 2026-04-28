// Microphone capture via MediaRecorder, with a parallel AnalyserNode that
// gives the waveform a real signal to react to.
//
// The hook returns:
//   start()       — request mic permission, begin recording
//   stop()        — stop recording, resolve with the Blob
//   level         — current normalised RMS (0–1) for the waveform
//   permission    — "unknown" | "prompt" | "granted" | "denied"
//
// We pick the best available MIME type at start time. webm/opus is the
// universal default on Chrome/Firefox; Safari ships MediaRecorder but
// records as MP4. Whisper accepts both.

import { useCallback, useEffect, useRef, useState } from "react";

type Permission = "unknown" | "prompt" | "granted" | "denied";

export interface AudioRecording {
  start: () => Promise<void>;
  stop: () => Promise<Blob>;
  cancel: () => void;
  level: number;
  isRecording: boolean;
  permission: Permission;
  error: string | null;
}

const MIME_PREFERENCES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/mp4",
  "audio/ogg;codecs=opus",
  "audio/ogg",
];

function pickMimeType(): string {
  if (typeof MediaRecorder === "undefined") return "";
  for (const m of MIME_PREFERENCES) {
    if (MediaRecorder.isTypeSupported?.(m)) return m;
  }
  return "";
}

export function useAudioRecording(): AudioRecording {
  const [level, setLevel] = useState(0);
  const [isRecording, setIsRecording] = useState(false);
  const [permission, setPermission] = useState<Permission>("unknown");
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRafRef = useRef<number | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const stopResolverRef = useRef<((b: Blob) => void) | null>(null);

  const cleanup = useCallback(() => {
    if (analyserRafRef.current !== null) {
      cancelAnimationFrame(analyserRafRef.current);
      analyserRafRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (audioCtxRef.current) {
      audioCtxRef.current.close().catch(() => {});
      audioCtxRef.current = null;
    }
    mediaRecorderRef.current = null;
    chunksRef.current = [];
    setLevel(0);
    setIsRecording(false);
  }, []);

  // Tear down on unmount in case a recording is mid-flight.
  useEffect(() => () => cleanup(), [cleanup]);

  const start = useCallback(async () => {
    setError(null);
    if (!navigator.mediaDevices?.getUserMedia) {
      setError("This browser doesn't support microphone capture.");
      return;
    }

    try {
      setPermission("prompt");
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setPermission("granted");
      streamRef.current = stream;

      // Set up the analyser branch so the waveform has real input to react to.
      const AudioCtx =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = new AudioCtx();
      audioCtxRef.current = ctx;
      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 512;
      source.connect(analyser);

      const buf = new Uint8Array(analyser.fftSize);
      const tick = () => {
        analyser.getByteTimeDomainData(buf);
        // Compute RMS deviation from 128 (centre).
        let sum = 0;
        for (let i = 0; i < buf.length; i++) {
          const v = (buf[i] - 128) / 128;
          sum += v * v;
        }
        const rms = Math.sqrt(sum / buf.length);
        setLevel(Math.min(1, rms * 3));
        analyserRafRef.current = requestAnimationFrame(tick);
      };
      analyserRafRef.current = requestAnimationFrame(tick);

      const mimeType = pickMimeType();
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        const resolver = stopResolverRef.current;
        stopResolverRef.current = null;
        cleanup();
        resolver?.(blob);
      };
      recorder.onerror = (e) => {
        setError(`Recorder error: ${(e as ErrorEvent).message ?? "unknown"}`);
        cleanup();
      };

      // Pass a timeslice so dataavailable fires every 250ms. Without this,
      // Safari's MediaRecorder can produce a malformed file on a quick
      // stop (incomplete moov atom in the mp4 container). With it the
      // encoder flushes regularly and the resulting blob is well-formed
      // even if the recording is short.
      recorder.start(250);
      setIsRecording(true);
    } catch (e) {
      setPermission("denied");
      setError(
        e instanceof Error
          ? e.name === "NotAllowedError"
            ? "We need microphone access to hear your question."
            : e.message
          : "Failed to start recording.",
      );
      cleanup();
    }
  }, [cleanup]);

  const stop = useCallback(async () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state === "inactive") {
      return new Blob();
    }
    return new Promise<Blob>((resolve) => {
      stopResolverRef.current = resolve;
      recorder.stop();
    });
  }, []);

  const cancel = useCallback(() => {
    stopResolverRef.current = null;
    cleanup();
  }, [cleanup]);

  return { start, stop, cancel, level, isRecording, permission, error };
}
