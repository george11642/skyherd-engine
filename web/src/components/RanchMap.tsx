/**
 * RanchMap — Canvas 2D ranch visualization.
 *
 * Draws: terrain with paddock polygons, dashed fence lines, hollow water tanks,
 * cattle dots (dust→danger by health), drone triangle with motion trail,
 * predator pulsing X, topography gradient fills, legend.
 *
 * Subscribes to "world.snapshot" SSE events, 60fps RAF loop.
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
  bounds: [number, number, number, number];
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

// Brand palette (matches CSS tokens)
const C = {
  bg_day:   "#0a0c10",
  bg_night: "#070810",
  grid:     "rgba(236,239,244,0.025)",
  paddock_border: "rgba(148,176,136,0.22)",
  fence:    "rgba(168,180,198,0.28)",
  cow_healthy: "#94b088",     // sage
  cow_stressed: "#d2b28a",    // dust
  cow_danger:   "#e0645a",    // danger
  drone:    "#78b4dc",        // sky
  predator: "#e0645a",        // danger
  water_high:   "#78b4dc",
  water_mid:    "#f0c350",
  water_low:    "#e0645a",
  text:     "rgba(168,180,198,0.8)",
  text_dim: "rgba(110,122,140,0.8)",
  trail:    "rgba(120,180,220,0.18)",
};

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

// Cow color: healthy=sage, stressed=dust, critical=danger
function cowColor(cow: Cow): string {
  const bcs = cow.bcs ?? 5;
  if (bcs < 3 || cow.state === "sick") return C.cow_danger;
  if (bcs < 4 || cow.state === "resting") return C.cow_stressed;
  return C.cow_healthy;
}

const TRAIL_LEN = 8;

export function RanchMap() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const snapshotRef = useRef<WorldSnapshot | null>(null);
  const animFrameRef = useRef<number>(0);
  const droneTrailRef = useRef<Array<[number, number]>>([]);
  const prevDroneRef = useRef<[number, number] | null>(null);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const snap = snapshotRef.current;

    const W = canvas.width / devicePixelRatio;
    const H = canvas.height / devicePixelRatio;

    // Scale for HiDPI
    ctx.save();
    ctx.scale(devicePixelRatio, devicePixelRatio);

    const px = (x: number) => x * W;
    const py = (y: number) => y * H;

    // --- Background ---
    const isNight = snap?.is_night ?? false;
    ctx.fillStyle = isNight ? C.bg_night : C.bg_day;
    ctx.fillRect(0, 0, W, H);

    // Subtle terrain texture — low-contrast gradient overlay
    const terrainGrad = ctx.createLinearGradient(0, 0, W, H);
    terrainGrad.addColorStop(0, "rgba(16,20,12,0.4)");
    terrainGrad.addColorStop(0.5, "rgba(12,16,10,0.0)");
    terrainGrad.addColorStop(1, "rgba(20,16,10,0.3)");
    ctx.fillStyle = terrainGrad;
    ctx.fillRect(0, 0, W, H);

    // Subtle dot grid
    ctx.fillStyle = C.grid;
    const gridStep = Math.round(W / 20);
    for (let gx = gridStep; gx < W; gx += gridStep) {
      for (let gy = gridStep; gy < H; gy += gridStep) {
        ctx.beginPath();
        ctx.arc(gx, gy, 0.8, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // --- Paddocks ---
    const paddocks: Paddock[] = snap?.paddocks ?? [
      { id: "north",  bounds: [0, 0, 0.5, 0.5], forage_pct: 72 },
      { id: "south",  bounds: [0.5, 0, 1, 0.5], forage_pct: 58 },
      { id: "east",   bounds: [0.5, 0.5, 1, 1], forage_pct: 84 },
      { id: "west",   bounds: [0, 0.5, 0.5, 1], forage_pct: 43 },
    ];
    for (const p of paddocks) {
      const [x0, y0, x1, y1] = p.bounds;
      const forage = p.forage_pct ?? 60;
      // Topography gradient per paddock based on forage health
      const green = Math.round(lerp(40, 120, forage / 100));
      const grad = ctx.createLinearGradient(px(x0), py(y0), px(x1), py(y1));
      grad.addColorStop(0, `rgba(20,${green + 20},10,0.12)`);
      grad.addColorStop(1, `rgba(10,${green},5,0.06)`);
      ctx.fillStyle = grad;
      ctx.fillRect(px(x0), py(y0), px(x1 - x0), py(y1 - y0));

      // Paddock border
      ctx.strokeStyle = C.paddock_border;
      ctx.lineWidth = 1;
      ctx.setLineDash([]);
      ctx.strokeRect(px(x0), py(y0), px(x1 - x0), py(y1 - y0));

      // Paddock label
      ctx.fillStyle = C.text_dim;
      ctx.font = `${Math.round(W * 0.019)}px "JetBrains Mono Variable", monospace`;
      ctx.fillText(p.id.toUpperCase(), px(x0) + 6, py(y0) + 15);

      // Forage % indicator (small bar along bottom of paddock)
      const barW = px(x1 - x0) - 8;
      const barH = 2;
      const barY = py(y1) - barH - 3;
      ctx.fillStyle = "rgba(38,45,58,0.6)";
      ctx.fillRect(px(x0) + 4, barY, barW, barH);
      ctx.fillStyle = forage > 60 ? C.cow_healthy : forage > 35 ? C.cow_stressed : C.cow_danger;
      ctx.fillRect(px(x0) + 4, barY, barW * (forage / 100), barH);
    }

    // --- Fence lines (perimeter, dashed) ---
    ctx.strokeStyle = C.fence;
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 6]);
    ctx.strokeRect(3, 3, W - 6, H - 6);
    ctx.setLineDash([]);

    // --- Water tanks ---
    const tanks: WaterTank[] = snap?.water_tanks ?? [
      { id: "A", pos: [0.25, 0.25], level_pct: 75 },
      { id: "B", pos: [0.75, 0.75], level_pct: 45 },
    ];
    for (const t of tanks) {
      const [tx, ty] = t.pos;
      const level = t.level_pct;
      const color = level > 60 ? C.water_high : level > 30 ? C.water_mid : C.water_low;
      const r = Math.max(5, Math.round(W * 0.018));
      const cx = px(tx), cy = py(ty);

      // Hollow square with fill % shown as vertical bar inside
      const sq = r * 1.4;
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.strokeRect(cx - sq, cy - sq, sq * 2, sq * 2);

      // Fill level bar inside square
      const fillH = (sq * 2) * (level / 100);
      ctx.fillStyle = hexToRgba(color, 0.25);
      ctx.fillRect(cx - sq, cy + sq - fillH, sq * 2, fillH);

      // Level text below
      ctx.fillStyle = color;
      ctx.font = `${Math.round(W * 0.016)}px "JetBrains Mono Variable", monospace`;
      ctx.textAlign = "center";
      ctx.fillText(`${Math.round(level)}%`, cx, cy + sq + 13);
      ctx.fillText(t.id, cx, cy);
      ctx.textAlign = "left";
    }

    // --- Cattle ---
    const cows: Cow[] = snap?.cows ?? [];
    for (const cow of cows) {
      const [cx, cy] = cow.pos;
      const color = cowColor(cow);
      const r = Math.max(2.5, Math.round(W * 0.01));
      ctx.beginPath();
      ctx.arc(px(cx), py(cy), r, 0, Math.PI * 2);
      ctx.fillStyle = hexToRgba(color, 0.85);
      ctx.fill();
    }

    // --- Drone motion trail ---
    const drone = snap?.drone;
    let droneX = 0.5, droneY = 0.5;
    if (drone) {
      if (Array.isArray(drone.pos)) {
        [droneX, droneY] = drone.pos;
      } else if (drone.lat !== undefined && drone.lon !== undefined) {
        droneX = Math.max(0.05, Math.min(0.95, (drone.lon - -106.48) / 0.05 + 0.5));
        droneY = Math.max(0.05, Math.min(0.95, (drone.lat - 34.10) / 0.05 + 0.5));
      }
    }

    // Update trail
    const prev = prevDroneRef.current;
    if (!prev || Math.abs(prev[0] - droneX) > 0.001 || Math.abs(prev[1] - droneY) > 0.001) {
      droneTrailRef.current = [...droneTrailRef.current, [droneX, droneY] as [number, number]].slice(-TRAIL_LEN);
      prevDroneRef.current = [droneX, droneY];
    }

    // Draw trail
    const trail = droneTrailRef.current;
    for (let i = 1; i < trail.length; i++) {
      const alpha = (i / trail.length) * 0.5;
      ctx.beginPath();
      ctx.moveTo(px(trail[i - 1][0]), py(trail[i - 1][1]));
      ctx.lineTo(px(trail[i][0]), py(trail[i][1]));
      ctx.strokeStyle = `rgba(120,180,220,${alpha})`;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    // Draw drone triangle
    const dSize = Math.max(7, Math.round(W * 0.022));
    const dx = px(droneX), dy = py(droneY);
    ctx.beginPath();
    ctx.moveTo(dx, dy - dSize);
    ctx.lineTo(dx + dSize * 0.65, dy + dSize * 0.55);
    ctx.lineTo(dx - dSize * 0.65, dy + dSize * 0.55);
    ctx.closePath();
    ctx.fillStyle = "rgba(120,180,220,0.85)";
    ctx.fill();
    ctx.strokeStyle = C.drone;
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Drone label
    ctx.fillStyle = C.drone;
    ctx.font = `${Math.round(W * 0.016)}px "JetBrains Mono Variable", monospace`;
    ctx.fillText("DRONE", dx + dSize + 4, dy + 4);

    // --- Predators ---
    const predators: Predator[] = snap?.predators ?? [];
    for (const pred of predators) {
      const [rx, ry] = pred.pos;
      const xSize = Math.max(6, Math.round(W * 0.02));
      const ppx = px(rx), ppy = py(ry);

      // Pulsing threat ring (CSS animation handles the pulse; here we just draw a static ring)
      ctx.beginPath();
      ctx.arc(ppx, ppy, xSize * 1.8, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(224,100,90,0.25)";
      ctx.lineWidth = 1;
      ctx.stroke();

      // X mark
      ctx.strokeStyle = C.predator;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(ppx - xSize, ppy - xSize);
      ctx.lineTo(ppx + xSize, ppy + xSize);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(ppx + xSize, ppy - xSize);
      ctx.lineTo(ppx - xSize, ppy + xSize);
      ctx.stroke();

      // Species label
      ctx.fillStyle = C.predator;
      ctx.font = `bold ${Math.round(W * 0.016)}px "JetBrains Mono Variable", monospace`;
      ctx.fillText(pred.species?.toUpperCase() ?? "PRED", ppx + xSize + 4, ppy + 4);
    }

    // --- Weather overlay ---
    const weather = snap?.weather;
    if (weather) {
      const overlayW = 200, overlayH = 20;
      ctx.fillStyle = "rgba(10,12,16,0.72)";
      ctx.fillRect(4, H - overlayH - 4, overlayW, overlayH);
      ctx.fillStyle = C.text_dim;
      ctx.font = `${Math.round(W * 0.015)}px "JetBrains Mono Variable", monospace`;
      ctx.fillText(
        `${weather.conditions?.toUpperCase() ?? ""} ${Math.round(weather.temp_f ?? 0)}°F ${Math.round(weather.wind_kt ?? 0)}kt`,
        9,
        H - 8,
      );
    }

    // --- Cattle count ---
    const countW = 88, countH = 20;
    ctx.fillStyle = "rgba(10,12,16,0.72)";
    ctx.fillRect(W - countW - 4, H - countH - 4, countW, countH);
    ctx.fillStyle = C.cow_healthy;
    ctx.font = `${Math.round(W * 0.015)}px "JetBrains Mono Variable", monospace`;
    ctx.textAlign = "right";
    ctx.fillText(`${cows.length} cattle`, W - 8, H - 8);
    ctx.textAlign = "left";

    ctx.restore();
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
    const handler = (payload: WorldSnapshot) => { snapshotRef.current = payload; };
    sse.on("world.snapshot", handler);
    return () => sse.off("world.snapshot", handler);
  }, []);

  // Resize observer — debounced
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    let timeout: ReturnType<typeof setTimeout>;
    const observer = new ResizeObserver(() => {
      clearTimeout(timeout);
      timeout = setTimeout(() => {
        const { width, height } = canvas.getBoundingClientRect();
        canvas.width = Math.round(width * devicePixelRatio);
        canvas.height = Math.round(height * devicePixelRatio);
      }, 50);
    });
    observer.observe(canvas);
    return () => { observer.disconnect(); clearTimeout(timeout); };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-full block"
      style={{ imageRendering: "crisp-edges" }}
      aria-label="Ranch map showing cattle positions, drone, water tanks, and predators"
      role="img"
      data-testid="ranch-map-canvas"
    />
  );
}
