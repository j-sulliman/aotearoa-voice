import { useEffect, useRef, useState } from "react";
import { LOCATIONS, type LocationId } from "../lib/locations";

interface MapViewProps {
  activeLocation: LocationId | null;
  pinnedIds: LocationId[];
  isPanning: boolean;
}

interface ViewCenter {
  lat: number;
  lng: number;
  zoom: number;
}

const INITIAL_VIEW: ViewCenter = { lat: -41.0, lng: 173.5, zoom: 1 };
const PAN_DURATION_MS = 1200;
const PAN_TARGET_ZOOM = 1.6;

export function MapView({ activeLocation, pinnedIds, isPanning }: MapViewProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [viewCenter, setViewCenter] = useState<ViewCenter>(INITIAL_VIEW);
  const animRef = useRef<number | null>(null);
  // Drives a redraw every frame while a location is active so the pin halo
  // pulses continuously. Without this the halo only animates during a pan.
  const [, setHaloTick] = useState(0);

  // Pan when active location changes
  useEffect(() => {
    if (!activeLocation) return;
    const target = LOCATIONS[activeLocation];
    if (!target) return;
    const start: ViewCenter = { ...viewCenter };
    const end: ViewCenter = { lat: target.lat, lng: target.lng, zoom: PAN_TARGET_ZOOM };
    const t0 = performance.now();
    const ease = (t: number) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);
    const tick = (now: number) => {
      const t = Math.min(1, (now - t0) / PAN_DURATION_MS);
      const e = ease(t);
      setViewCenter({
        lat: start.lat + (end.lat - start.lat) * e,
        lng: start.lng + (end.lng - start.lng) * e,
        zoom: start.zoom + (end.zoom - start.zoom) * e,
      });
      if (t < 1) animRef.current = requestAnimationFrame(tick);
    };
    animRef.current = requestAnimationFrame(tick);
    return () => {
      if (animRef.current !== null) cancelAnimationFrame(animRef.current);
    };
    // viewCenter intentionally NOT a dep — it'd retrigger on every frame.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeLocation]);

  // Halo redraw loop while an active pin exists
  useEffect(() => {
    if (!activeLocation) return;
    let raf = 0;
    const loop = () => {
      setHaloTick((n) => (n + 1) % 1_000_000);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [activeLocation]);

  // Draw on every meaningful change
  useEffect(() => {
    const cv = canvasRef.current;
    if (!cv) return;
    const dpr = window.devicePixelRatio || 1;
    const rect = cv.getBoundingClientRect();
    cv.width = rect.width * dpr;
    cv.height = rect.height * dpr;
    const ctx = cv.getContext("2d");
    if (!ctx) return;
    ctx.scale(dpr, dpr);
    const w = rect.width;
    const h = rect.height;

    // BG ocean
    ctx.fillStyle = "#0a2540";
    ctx.fillRect(0, 0, w, h);

    // Subtle grid
    ctx.strokeStyle = "rgba(244,241,236,0.04)";
    ctx.lineWidth = 1;
    for (let i = 0; i < w; i += 40) {
      ctx.beginPath();
      ctx.moveTo(i, 0);
      ctx.lineTo(i, h);
      ctx.stroke();
    }
    for (let j = 0; j < h; j += 40) {
      ctx.beginPath();
      ctx.moveTo(0, j);
      ctx.lineTo(w, j);
      ctx.stroke();
    }

    drawLandmass(ctx, NORTH_ISLAND, w, h, viewCenter);
    drawLandmass(ctx, SOUTH_ISLAND, w, h, viewCenter);
    drawLandmass(ctx, STEWART, w, h, viewCenter);

    pinnedIds.forEach((id) => {
      const loc = LOCATIONS[id];
      if (!loc) return;
      const { x, y } = project(loc.lat, loc.lng, w, h, viewCenter, viewCenter.zoom);
      const isActive = id === activeLocation;
      drawPin(ctx, x, y, loc.name, isActive);
    });
  });

  return (
    <div className="map-wrap">
      <canvas ref={canvasRef} className="map-canvas" />
      <div className="map-overlay-tl">
        <div className="map-coord">
          <span className="mono">{Math.abs(viewCenter.lat).toFixed(3)}°S</span>
          <span className="mono">{Math.abs(viewCenter.lng).toFixed(3)}°E</span>
        </div>
      </div>
      <div className="map-overlay-br">
        <div className="map-legend">
          <span className="legend-dot" />
          <span>{pinnedIds.length} pinned</span>
        </div>
      </div>
      {isPanning && activeLocation && (
        <div className="pan-indicator">PAN · {LOCATIONS[activeLocation]?.name}</div>
      )}
    </div>
  );
}

function project(
  lat: number,
  lng: number,
  w: number,
  h: number,
  center: ViewCenter,
  zoom: number,
): { x: number; y: number } {
  const scale = 35 * zoom;
  const dx = (lng - center.lng) * scale;
  const dy = -(lat - center.lat) * scale;
  return { x: w / 2 + dx, y: h / 2 + dy };
}

function drawLandmass(
  ctx: CanvasRenderingContext2D,
  points: ReadonlyArray<readonly [number, number]>,
  w: number,
  h: number,
  center: ViewCenter,
): void {
  ctx.beginPath();
  const scale = 35 * center.zoom;
  points.forEach(([lat, lng], i) => {
    const x = w / 2 + (lng - center.lng) * scale;
    const y = h / 2 - (lat - center.lat) * scale;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.closePath();
  ctx.fillStyle = "#1d3a5f";
  ctx.fill();
  ctx.strokeStyle = "rgba(244,241,236,0.18)";
  ctx.lineWidth = 0.6;
  ctx.stroke();
}

function drawPin(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  label: string,
  active: boolean,
): void {
  if (active) {
    const t = (Date.now() % 1600) / 1600;
    const r = 8 + t * 28;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.strokeStyle = `rgba(200,54,45,${(1 - t) * 0.6})`;
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }
  ctx.beginPath();
  ctx.arc(x, y, active ? 7 : 5, 0, Math.PI * 2);
  ctx.fillStyle = "#c8362d";
  ctx.fill();
  ctx.strokeStyle = "#f4f1ec";
  ctx.lineWidth = 1.5;
  ctx.stroke();

  if (active) {
    ctx.font = "500 13px 'Fraunces', serif";
    const tw = ctx.measureText(label).width;
    ctx.fillStyle = "rgba(10,37,64,0.85)";
    ctx.fillRect(x + 12, y - 9, tw + 14, 22);
    ctx.fillStyle = "#f4f1ec";
    ctx.fillText(label, x + 19, y + 6);
  }
}

// Stylised lat/lng polygons — not topographically precise. Ported verbatim
// from the design prototype.
const NORTH_ISLAND: ReadonlyArray<readonly [number, number]> = [
  [-34.4, 172.7], [-34.6, 173.0], [-35.2, 173.5], [-35.8, 174.3], [-36.4, 174.7],
  [-36.9, 175.0], [-37.2, 175.6], [-37.6, 176.0], [-37.7, 176.8], [-37.9, 177.5],
  [-38.5, 178.2], [-39.4, 178.0], [-40.2, 177.5], [-40.6, 176.7], [-41.3, 175.3],
  [-41.5, 174.8], [-41.0, 174.5], [-40.4, 174.0], [-39.8, 173.8], [-39.0, 173.7],
  [-38.6, 174.0], [-38.2, 174.6], [-37.8, 174.8], [-37.0, 174.5], [-36.5, 174.0],
  [-35.9, 173.5], [-35.3, 173.0], [-34.8, 172.8], [-34.4, 172.7],
];

const SOUTH_ISLAND: ReadonlyArray<readonly [number, number]> = [
  [-40.5, 172.7], [-40.8, 173.5], [-41.2, 174.3], [-41.6, 174.3], [-42.0, 173.8],
  [-42.6, 173.5], [-43.4, 172.8], [-44.0, 171.4], [-44.6, 171.1], [-45.2, 170.8],
  [-45.8, 170.7], [-46.3, 169.9], [-46.7, 168.5], [-46.6, 167.9], [-46.0, 167.3],
  [-45.4, 167.0], [-44.9, 166.9], [-44.4, 167.5], [-43.7, 168.3], [-43.0, 169.2],
  [-42.4, 170.2], [-41.8, 171.5], [-41.2, 172.0], [-40.7, 172.3], [-40.5, 172.7],
];

const STEWART: ReadonlyArray<readonly [number, number]> = [
  [-46.8, 167.7], [-46.9, 168.1], [-47.2, 168.2], [-47.3, 168.0], [-47.1, 167.6], [-46.8, 167.7],
];
