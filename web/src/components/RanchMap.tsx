/**
 * RanchMap — Canvas 2D ranch visualization.
 *
 * Draws: terrain background, paddocks, fence lines, water tanks (color by level),
 * cows (green dots), drone (cyan triangle), predators (red X).
 *
 * Subscribes to "world.snapshot" SSE events and re-renders on each update.
 */

import { useEffect, useRef, useCallback } from "react";
import { getSSE } from "@/lib/sse";

interface Cow {
  id: string;
  pos: [number, number];
  state?: string;
  bcs?: number;
}

interface Predator {
  id: string;
  pos: [number, number];
  species?: string;
  threat_level?: string;
}

interface Drone {
  lat?: number;
  lon?: number;
  pos?: [number, number];
  state?: string;
  battery_pct?: number;
  alt_m?: number;
}

interface Paddock {
  id: string;
  bounds: [number, number, number, number]; // [x0, y0, x1, y1] normalized 0-1
  forage_pct?: number;
}

interface WaterTank {
  id: string;
  pos: [number, number];
  level_pct: number;
}

interface WorldSnapshot {
  cows: Cow[];
  predators: Predator[];
  drone?: Drone;
  paddocks?: Paddock[];
  water_tanks?: WaterTank[];
  is_night?: boolean;
  weather?: { conditions: string; temp_f: number; wind_kt: number };
}

const COLORS = {
  terrain_day: "#1a2a1a",
  terrain_night: "#0d1a0d",
  paddock: "rgba(34,197,94,0.08)",
  paddock_border: "rgba(34,197,94,0.25)",
  fence: "rgba(203,213,225,0.30)",
  cow_grazing: "#22c55e",
  cow_resting: "#86efac",
  cow_walking: "#4ade80",
  cow_default: "#22c55e",
  drone: "#38bdf8",
  predator: "#ef4444",
  water_high: "#38bdf8",
  water_medium: "#f59e0b",
  water_low: "#ef4444",
  text: "rgba(226,232,240,0.7)",
};

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

export function RanchMap() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const snapshotRef = useRef<WorldSnapshot | null>(null);
  const animFrameRef = useRef<number>(0);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const snap = snapshotRef.current;

    const W = canvas.width;
    const H = canvas.height;

    // Convert normalized [0,1] → canvas pixels
    const px = (x: number) => x * W;
    const py = (y: number) => y * H;

    // --- Background ---
    const isNight = snap?.is_night ?? false;
    ctx.fillStyle = isNight ? COLORS.terrain_night : COLORS.terrain_day;
    ctx.fillRect(0, 0, W, H);

    // --- Subtle grid ---
    ctx.strokeStyle = "rgba(255,255,255,0.03)";
    ctx.lineWidth = 1;
    const gridSize = 5;
    for (let i = 1; i < gridSize; i++) {
      ctx.beginPath();
      ctx.moveTo(px(i / gridSize), 0);
      ctx.lineTo(px(i / gridSize), H);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(0, py(i / gridSize));
      ctx.lineTo(W, py(i / gridSize));
      ctx.stroke();
    }

    // --- Paddocks ---
    const paddocks: Paddock[] = snap?.paddocks ?? [
      { id: "north", bounds: [0, 0, 0.5, 0.5], forage_pct: 72 },
      { id: "south", bounds: [0.5, 0, 1, 0.5], forage_pct: 58 },
      { id: "east", bounds: [0.5, 0.5, 1, 1], forage_pct: 84 },
      { id: "west", bounds: [0, 0.5, 0.5, 1], forage_pct: 43 },
    ];
    for (const p of paddocks) {
      const [x0, y0, x1, y1] = p.bounds;
      const forage = p.forage_pct ?? 60;
      // Color paddock by forage health
      const green = Math.round(lerp(80, 200, forage / 100));
      ctx.fillStyle = `rgba(34,${green},60,0.10)`;
      ctx.fillRect(px(x0), py(y0), px(x1 - x0), py(y1 - y0));
      ctx.strokeStyle = COLORS.paddock_border;
      ctx.lineWidth = 1.5;
      ctx.strokeRect(px(x0), py(y0), px(x1 - x0), py(y1 - y0));
      // Label
      ctx.fillStyle = COLORS.text;
      ctx.font = `${Math.round(W * 0.022)}px monospace`;
      ctx.fillText(p.id, px(x0) + 6, py(y0) + 16);
    }

    // --- Fence lines (perimeter) ---
    ctx.strokeStyle = COLORS.fence;
    ctx.lineWidth = 2;
    ctx.strokeRect(2, 2, W - 4, H - 4);

    // --- Water tanks ---
    const tanks: WaterTank[] = snap?.water_tanks ?? [
      { id: "A", pos: [0.25, 0.25], level_pct: 75 },
      { id: "B", pos: [0.75, 0.75], level_pct: 45 },
    ];
    for (const t of tanks) {
      const [tx, ty] = t.pos;
      const level = t.level_pct;
      const color =
        level > 60 ? COLORS.water_high : level > 30 ? COLORS.water_medium : COLORS.water_low;
      const r = Math.round(W * 0.018);
      ctx.beginPath();
      ctx.arc(px(tx), py(ty), r, 0, Math.PI * 2);
      ctx.fillStyle = color + "33";
      ctx.fill();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.stroke();
      // Level text
      ctx.fillStyle = color;
      ctx.font = `bold ${Math.round(W * 0.018)}px monospace`;
      ctx.textAlign = "center";
      ctx.fillText(`${Math.round(level)}%`, px(tx), py(ty) + r + 14);
      ctx.textAlign = "left";
    }

    // --- Cows ---
    const cows: Cow[] = snap?.cows ?? [];
    for (const cow of cows) {
      const [cx, cy] = cow.pos;
      const stateColor =
        cow.state === "resting"
          ? COLORS.cow_resting
          : cow.state === "walking"
            ? COLORS.cow_walking
            : COLORS.cow_default;
      const r = Math.round(W * 0.012);
      ctx.beginPath();
      ctx.arc(px(cx), py(cy), r, 0, Math.PI * 2);
      ctx.fillStyle = stateColor + "cc";
      ctx.fill();
      ctx.strokeStyle = stateColor;
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    // --- Drone ---
    const drone = snap?.drone;
    let droneX = 0.5;
    let droneY = 0.5;
    if (drone) {
      if (Array.isArray(drone.pos)) {
        [droneX, droneY] = drone.pos;
      } else if (drone.lat !== undefined && drone.lon !== undefined) {
        // Map lat/lon to canvas (rough NM ranch area)
        droneX = (drone.lon - -106.48) / 0.05 + 0.5;
        droneY = (drone.lat - 34.10) / 0.05 + 0.5;
        droneX = Math.max(0.05, Math.min(0.95, droneX));
        droneY = Math.max(0.05, Math.min(0.95, droneY));
      }
    }
    // Triangle pointing up
    const dSize = Math.round(W * 0.025);
    const dx = px(droneX);
    const dy = py(droneY);
    ctx.beginPath();
    ctx.moveTo(dx, dy - dSize);
    ctx.lineTo(dx + dSize * 0.7, dy + dSize * 0.6);
    ctx.lineTo(dx - dSize * 0.7, dy + dSize * 0.6);
    ctx.closePath();
    ctx.fillStyle = COLORS.drone + "cc";
    ctx.fill();
    ctx.strokeStyle = COLORS.drone;
    ctx.lineWidth = 1.5;
    ctx.stroke();
    // Drone label
    ctx.fillStyle = COLORS.drone;
    ctx.font = `${Math.round(W * 0.018)}px monospace`;
    ctx.fillText("DRONE", dx + dSize + 3, dy);

    // --- Predators ---
    const predators: Predator[] = snap?.predators ?? [];
    for (const pred of predators) {
      const [rx, ry] = pred.pos;
      const xSize = Math.round(W * 0.022);
      const ppx = px(rx);
      const ppy = py(ry);
      ctx.strokeStyle = COLORS.predator;
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      ctx.moveTo(ppx - xSize, ppy - xSize);
      ctx.lineTo(ppx + xSize, ppy + xSize);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(ppx + xSize, ppy - xSize);
      ctx.lineTo(ppx - xSize, ppy + xSize);
      ctx.stroke();
      // Label
      ctx.fillStyle = COLORS.predator;
      ctx.font = `bold ${Math.round(W * 0.018)}px monospace`;
      ctx.fillText(pred.species ?? "PRED", ppx + xSize + 3, ppy);
    }

    // --- Status overlay ---
    const weather = snap?.weather;
    if (weather) {
      ctx.fillStyle = "rgba(15,17,23,0.75)";
      ctx.fillRect(4, H - 26, 200, 22);
      ctx.fillStyle = "rgba(148,163,184,0.8)";
      ctx.font = `${Math.round(W * 0.016)}px monospace`;
      ctx.fillText(
        `${weather.conditions?.toUpperCase() ?? ""} ${Math.round(weather.temp_f ?? 0)}°F ${Math.round(weather.wind_kt ?? 0)}kt`,
        8,
        H - 10,
      );
    }

    // Cow count
    ctx.fillStyle = "rgba(15,17,23,0.75)";
    ctx.fillRect(W - 90, H - 26, 86, 22);
    ctx.fillStyle = COLORS.cow_default;
    ctx.font = `${Math.round(W * 0.016)}px monospace`;
    ctx.textAlign = "right";
    ctx.fillText(`${cows.length} cattle`, W - 6, H - 10);
    ctx.textAlign = "left";
  }, []);

  // RAF loop
  useEffect(() => {
    let running = true;
    const loop = () => {
      if (!running) return;
      draw();
      animFrameRef.current = requestAnimationFrame(loop);
    };
    animFrameRef.current = requestAnimationFrame(loop);
    return () => {
      running = false;
      cancelAnimationFrame(animFrameRef.current);
    };
  }, [draw]);

  // SSE subscription
  useEffect(() => {
    const sse = getSSE();
    const handler = (payload: WorldSnapshot) => {
      snapshotRef.current = payload;
    };
    sse.on("world.snapshot", handler);
    return () => sse.off("world.snapshot", handler);
  }, []);

  // Resize observer
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const observer = new ResizeObserver(() => {
      const { width, height } = canvas.getBoundingClientRect();
      canvas.width = width * devicePixelRatio;
      canvas.height = height * devicePixelRatio;
      const ctx = canvas.getContext("2d");
      if (ctx) ctx.scale(devicePixelRatio, devicePixelRatio);
    });
    observer.observe(canvas);
    return () => observer.disconnect();
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-full block"
      style={{ imageRendering: "crisp-edges" }}
      aria-label="Ranch map showing cattle, drone, and predator positions"
      role="img"
      data-testid="ranch-map-canvas"
    />
  );
}
