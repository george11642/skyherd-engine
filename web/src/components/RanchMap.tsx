/**
 * RanchMap — Canvas 2D ranch visualization with shared RAF tween pipeline.
 *
 * Phase 10.5 (DASH10-08, DASH10-09, scope expansion): every moving entity
 * on the map — cows, drone, drone trail, predators — now interpolates
 * smoothly between SSE `world.snapshot` ticks using a single shared RAF
 * loop + ease-out-cubic tweens. A WebGL2 `TerrainLayer` is mounted beneath
 * the 2D canvas to hint at landscape texture (raw WebGL, no deps).
 *
 * Layer order (painter's algorithm): WebGL terrain → paddock fills → paddock
 * labels (pushed to corners) → fences → water tanks → cows (+ health ring
 * for non-healthy) → cow tag labels (only for watch/sick/calving) → drone
 * trail → drone triangle → drone label (smart offset, never collides with
 * EAST) → predators + threat ring → weather overlay (bottom-left) → cattle
 * legend (bottom-right, summarizing herd health).
 *
 * Subscribes to:
 *   - "world.snapshot" SSE — updates cow/drone/predator positions, which
 *     retarget the per-entity tween records via `retarget(...)`.
 *   - "scenario.active" / "scenario.ended" — drives the ScenarioBreadcrumb
 *     and the `scenarioGlowZone` that tints a paddock when a scenario names
 *     a zone (coyote → NE, water_drop → where tank is, etc.).
 *
 * 60fps RAF loop, HiDPI aware. `prefers-reduced-motion: reduce` makes all
 * tweens snap-to-target for accessibility.
 */

import { useEffect, useRef, useCallback, useState } from "react";
import { getSSE } from "@/lib/sse";
import { TerrainLayer } from "@/components/shared/TerrainLayer";
import {
  createTween,
  retarget as retargetTween,
  tweenValue,
  lerpRgb,
  prefersReducedMotion,
  lerp,
  type TweenState,
} from "@/lib/tween";

interface Cow {
  id: string;
  tag?: string;
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

// Tween durations (ms) — tuned per entity so drones feel snappier than cows.
const COW_POS_MS = 800;
const COW_COLOR_MS = 400;
const COW_FADE_IN_MS = 500;
const DRONE_POS_MS = 600;
const PREDATOR_FADE_MS = 500;
const TRAIL_FADE_MS = 400;

// Brand palette (matches CSS tokens)
const C = {
  bg_day: "#0a0c10",
  bg_night: "#070810",
  grid: "rgba(236,239,244,0.025)",
  paddock_border: "rgba(148,176,136,0.22)",
  fence: "rgba(168,180,198,0.28)",
  // Cow health states — colorblind-safe triple (hue differences alongside
  // luminance differences so deuteranopes can still distinguish)
  cow_healthy: "#94b088", // sage
  cow_watch: "#d2b28a", // dust
  cow_sick: "#e0645a", // danger
  cow_calving: "#78b4dc", // sky
  drone: "#78b4dc", // sky
  predator: "#e0645a", // danger
  water_high: "#78b4dc",
  water_mid: "#f0c350",
  water_low: "#e0645a",
  text: "rgba(168,180,198,0.8)",
  text_dim: "rgba(110,122,140,0.8)",
  text_bright: "rgba(236,239,244,0.95)",
  trail: "rgba(120,180,220,0.18)",
  glow_coyote: "rgba(255,143,60,0.12)",
  glow_water: "rgba(120,180,220,0.12)",
  glow_sick: "rgba(224,100,90,0.12)",
};

// RGB triples for the health-color cross-fade.
const COW_RGB: Record<CowHealth, [number, number, number]> = {
  healthy: [148, 176, 136],
  watch: [210, 178, 138],
  sick: [224, 100, 90],
  calving: [120, 180, 220],
};

type CowHealth = "healthy" | "watch" | "sick" | "calving";

function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

// Cow health classification from bcs + state — single source of truth
export function classifyCow(cow: Cow): CowHealth {
  if (cow.state === "calving" || cow.state === "labor") return "calving";
  if (cow.state === "sick") return "sick";
  const bcs = cow.bcs ?? 5;
  if (bcs < 3) return "sick";
  if (bcs < 4 || cow.state === "resting") return "watch";
  return "healthy";
}

function cowColor(health: CowHealth): string {
  switch (health) {
    case "sick":
      return C.cow_sick;
    case "calving":
      return C.cow_calving;
    case "watch":
      return C.cow_watch;
    default:
      return C.cow_healthy;
  }
}

const TRAIL_LEN = 12;

// Map scenario names → paddock id or zone hint for the glow overlay
function scenarioToZone(name?: string): { paddock?: string; color?: string } {
  if (!name) return {};
  const n = name.toLowerCase();
  if (n.includes("coyote") || n.includes("fence")) {
    return { paddock: "north", color: C.glow_coyote };
  }
  if (n.includes("water")) {
    return { paddock: "north", color: C.glow_water };
  }
  if (n.includes("sick") || n.includes("health")) {
    return { paddock: "east", color: C.glow_sick };
  }
  if (n.includes("calving")) {
    return { paddock: "west", color: C.glow_water };
  }
  if (n.includes("storm")) {
    return { paddock: "south", color: C.glow_coyote };
  }
  return {};
}

// Paddock label corner placement — always push to an OUTSIDE corner so labels
// never collide with map-center symbols (drone triangle, center-clustered cows).
function paddockLabelAnchor(
  p: Paddock,
  px: (x: number) => number,
  py: (y: number) => number,
): { x: number; y: number; align: CanvasTextAlign } {
  const [x0, y0, x1, y1] = p.bounds;
  const leftHalf = x0 < 0.5;
  const topHalf = y0 < 0.5;
  if (leftHalf && topHalf) return { x: px(x0) + 6, y: py(y0) + 14, align: "left" };
  if (!leftHalf && topHalf) return { x: px(x1) - 6, y: py(y0) + 14, align: "right" };
  if (leftHalf && !topHalf) return { x: px(x0) + 6, y: py(y1) - 6, align: "left" };
  return { x: px(x1) - 6, y: py(y1) - 6, align: "right" };
}

/** Drone label smart offset — avoids collision with paddock labels. */
function droneLabelOffset(
  dx: number,
  dy: number,
  W: number,
  H: number,
): { x: number; y: number; align: CanvasTextAlign } {
  const centerX = W / 2;
  const centerY = H / 2;
  const rightSide = dx < centerX;
  const belowCenter = dy < centerY;
  const offsetX = rightSide ? 12 : -12;
  const offsetY = belowCenter ? 18 : -8;
  return {
    x: dx + offsetX,
    y: dy + offsetY,
    align: rightSide ? "left" : "right",
  };
}

// ---------------------------------------------------------------------------
// Entity tween state — shared RAF pipeline records
// ---------------------------------------------------------------------------

interface CowTweenRec {
  xTween: TweenState;
  yTween: TweenState;
  fadeStartMs: number; // when the cow first appeared (for fade-in)
  health: CowHealth;
  /** RGB at the start of the current color cross-fade. */
  colorFrom: [number, number, number];
  /** Target RGB for the current health state. */
  colorTo: [number, number, number];
  /** `performance.now()` at which the current color cross-fade started. */
  colorStartMs: number;
}

interface PredatorTweenRec {
  xTween: TweenState;
  yTween: TweenState;
  fadeStartMs: number;
  phase: number;
}

interface DroneTweenRec {
  xTween: TweenState;
  yTween: TweenState;
}

interface TrailPoint {
  x: number;
  y: number;
  spawnMs: number;
}

interface EntityState {
  cows: Map<string, CowTweenRec>;
  predators: Map<string, PredatorTweenRec>;
  drone: DroneTweenRec | null;
  trail: TrailPoint[];
  /** Last drone target pos — so we only push trail points on change. */
  lastDroneTarget: [number, number] | null;
  /** Set of cow IDs seen in the last snapshot — for cull detection. */
  seenCowIds: Set<string>;
  seenPredatorIds: Set<string>;
}

function createEntityState(): EntityState {
  return {
    cows: new Map(),
    predators: new Map(),
    drone: null,
    trail: [],
    lastDroneTarget: null,
    seenCowIds: new Set(),
    seenPredatorIds: new Set(),
  };
}

/**
 * Apply a new snapshot to the entity-state tweens. Pure-ish: mutates `state`
 * in place (keeps allocation count low on the RAF hot path), but never
 * touches the incoming `snap`. Called from the `world.snapshot` SSE handler.
 */
export function applySnapshotToTweens(
  state: EntityState,
  snap: WorldSnapshot,
  nowMs: number,
  reduceMotion: boolean,
): void {
  // --- Cows ---
  const nextCowIds = new Set<string>();
  for (const cow of snap.cows ?? []) {
    nextCowIds.add(cow.id);
    const [tx, ty] = cow.pos;
    const health = classifyCow(cow);
    const existing = state.cows.get(cow.id);
    if (!existing) {
      // Brand-new cow: seed at target position with fade-in.
      state.cows.set(cow.id, {
        xTween: createTween(tx, tx, nowMs, reduceMotion ? 0 : COW_POS_MS),
        yTween: createTween(ty, ty, nowMs, reduceMotion ? 0 : COW_POS_MS),
        fadeStartMs: nowMs,
        health,
        colorFrom: COW_RGB[health],
        colorTo: COW_RGB[health],
        colorStartMs: nowMs - COW_COLOR_MS, // fully on
      });
    } else {
      existing.xTween = retargetTween(
        existing.xTween,
        tx,
        nowMs,
        reduceMotion ? 0 : COW_POS_MS,
      );
      existing.yTween = retargetTween(
        existing.yTween,
        ty,
        nowMs,
        reduceMotion ? 0 : COW_POS_MS,
      );
      if (existing.health !== health) {
        // Cross-fade from the previously-blended color to the new target.
        const pColor = tweenCowColor(existing, nowMs);
        existing.colorFrom = pColor;
        existing.colorTo = COW_RGB[health];
        existing.colorStartMs = reduceMotion ? nowMs - COW_COLOR_MS : nowMs;
        existing.health = health;
      }
    }
  }
  // Cull cows no longer in the snapshot.
  for (const id of state.cows.keys()) {
    if (!nextCowIds.has(id)) state.cows.delete(id);
  }
  state.seenCowIds = nextCowIds;

  // --- Predators ---
  const nextPredIds = new Set<string>();
  for (const pred of snap.predators ?? []) {
    nextPredIds.add(pred.id);
    const [tx, ty] = pred.pos;
    const existing = state.predators.get(pred.id);
    if (!existing) {
      state.predators.set(pred.id, {
        xTween: createTween(tx, tx, nowMs, reduceMotion ? 0 : COW_POS_MS),
        yTween: createTween(ty, ty, nowMs, reduceMotion ? 0 : COW_POS_MS),
        fadeStartMs: nowMs,
        phase: Math.random(),
      });
    } else {
      existing.xTween = retargetTween(
        existing.xTween,
        tx,
        nowMs,
        reduceMotion ? 0 : COW_POS_MS,
      );
      existing.yTween = retargetTween(
        existing.yTween,
        ty,
        nowMs,
        reduceMotion ? 0 : COW_POS_MS,
      );
    }
  }
  for (const id of state.predators.keys()) {
    if (!nextPredIds.has(id)) state.predators.delete(id);
  }
  state.seenPredatorIds = nextPredIds;

  // --- Drone ---
  const drone = snap.drone;
  if (drone) {
    let droneX = 0.5;
    let droneY = 0.5;
    if (Array.isArray(drone.pos)) {
      [droneX, droneY] = drone.pos;
    } else if (drone.lat !== undefined && drone.lon !== undefined) {
      droneX = Math.max(0.05, Math.min(0.95, (drone.lon - -106.48) / 0.05 + 0.5));
      droneY = Math.max(0.05, Math.min(0.95, (drone.lat - 34.1) / 0.05 + 0.5));
    }
    if (!state.drone) {
      state.drone = {
        xTween: createTween(droneX, droneX, nowMs, reduceMotion ? 0 : DRONE_POS_MS),
        yTween: createTween(droneY, droneY, nowMs, reduceMotion ? 0 : DRONE_POS_MS),
      };
    } else {
      state.drone.xTween = retargetTween(
        state.drone.xTween,
        droneX,
        nowMs,
        reduceMotion ? 0 : DRONE_POS_MS,
      );
      state.drone.yTween = retargetTween(
        state.drone.yTween,
        droneY,
        nowMs,
        reduceMotion ? 0 : DRONE_POS_MS,
      );
    }
    // Trail — append only on meaningful change.
    const prev = state.lastDroneTarget;
    if (
      !prev ||
      Math.abs(prev[0] - droneX) > 0.001 ||
      Math.abs(prev[1] - droneY) > 0.001
    ) {
      state.trail.push({ x: droneX, y: droneY, spawnMs: nowMs });
      if (state.trail.length > TRAIL_LEN) {
        state.trail.splice(0, state.trail.length - TRAIL_LEN);
      }
      state.lastDroneTarget = [droneX, droneY];
    }
  }
}

/** Current eased RGB for the cow's color cross-fade. */
function tweenCowColor(
  rec: CowTweenRec,
  nowMs: number,
): [number, number, number] {
  const raw =
    COW_COLOR_MS <= 0
      ? 1
      : (nowMs - rec.colorStartMs) / COW_COLOR_MS;
  const t = raw >= 1 ? 1 : raw <= 0 ? 0 : raw;
  // Linear blend (eased externally); color cross-fade looks best linear.
  return [
    rec.colorFrom[0] + (rec.colorTo[0] - rec.colorFrom[0]) * t,
    rec.colorFrom[1] + (rec.colorTo[1] - rec.colorFrom[1]) * t,
    rec.colorFrom[2] + (rec.colorTo[2] - rec.colorFrom[2]) * t,
  ];
}

/**
 * RanchMapProps — optional snapshot override for tests & storybook fixtures.
 */
interface RanchMapProps {
  snapshot?: WorldSnapshot;
}

export function RanchMap({ snapshot: snapshotProp }: RanchMapProps = {}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const snapshotRef = useRef<WorldSnapshot | null>(snapshotProp ?? null);
  const entityRef = useRef<EntityState>(createEntityState());
  const animFrameRef = useRef<number>(0);
  const predatorPhaseRef = useRef<Map<string, number>>(new Map());
  const scenarioZoneRef = useRef<{ paddock?: string; color?: string }>({});
  const reduceMotionRef = useRef<boolean>(prefersReducedMotion());

  // Keep snapshotRef in sync with the snapshot prop across re-renders AND
  // fold the prop through the tween pipeline for test-driven rendering.
  if (snapshotProp !== undefined && snapshotRef.current !== snapshotProp) {
    snapshotRef.current = snapshotProp;
    const nowMs =
      typeof performance !== "undefined" && typeof performance.now === "function"
        ? performance.now()
        : Date.now();
    applySnapshotToTweens(
      entityRef.current,
      snapshotProp,
      nowMs,
      reduceMotionRef.current,
    );
  }

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const snap = snapshotRef.current;
    const state = entityRef.current;
    const nowMs =
      typeof performance !== "undefined" && typeof performance.now === "function"
        ? performance.now()
        : Date.now();

    const W = canvas.width / devicePixelRatio;
    const H = canvas.height / devicePixelRatio;

    ctx.save();
    ctx.scale(devicePixelRatio, devicePixelRatio);

    const px = (x: number) => x * W;
    const py = (y: number) => y * H;

    // --- Background (deliberately mostly transparent over WebGL terrain) ---
    const isNight = snap?.is_night ?? false;
    // Keep a base fill so scenario tints & paddock shading still read
    // correctly; WebGL terrain already provides the base landscape hint.
    ctx.fillStyle = isNight ? "rgba(7,8,16,0.55)" : "rgba(10,12,16,0.45)";
    ctx.fillRect(0, 0, W, H);

    // Subtle terrain wash (kept from Phase 10 for continuity)
    const terrainGrad = ctx.createLinearGradient(0, 0, W, H);
    terrainGrad.addColorStop(0, "rgba(16,20,12,0.22)");
    terrainGrad.addColorStop(0.5, "rgba(12,16,10,0.0)");
    terrainGrad.addColorStop(1, "rgba(20,16,10,0.18)");
    ctx.fillStyle = terrainGrad;
    ctx.fillRect(0, 0, W, H);

    // Dot grid
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
      { id: "north", bounds: [0, 0, 0.5, 0.5], forage_pct: 72 },
      { id: "south", bounds: [0.5, 0, 1, 0.5], forage_pct: 58 },
      { id: "east", bounds: [0.5, 0.5, 1, 1], forage_pct: 84 },
      { id: "west", bounds: [0, 0.5, 0.5, 1], forage_pct: 43 },
    ];
    const activeZone = scenarioZoneRef.current;
    for (const p of paddocks) {
      const [x0, y0, x1, y1] = p.bounds;
      const forage = p.forage_pct ?? 60;
      const green = Math.round(lerp(40, 120, forage / 100));
      const grad = ctx.createLinearGradient(px(x0), py(y0), px(x1), py(y1));
      grad.addColorStop(0, `rgba(20,${green + 20},10,0.12)`);
      grad.addColorStop(1, `rgba(10,${green},5,0.06)`);
      ctx.fillStyle = grad;
      ctx.fillRect(px(x0), py(y0), px(x1 - x0), py(y1 - y0));

      if (activeZone.paddock === p.id && activeZone.color) {
        const nowS = nowMs / 1000;
        const pulse = 0.5 + 0.5 * Math.sin(nowS * 1.3);
        const glowBase = activeZone.color;
        const match = glowBase.match(/rgba\(([^)]+)\)/);
        if (match) {
          const parts = match[1].split(",").map((s) => s.trim());
          const alpha = Math.min(0.4, 0.12 + pulse * 0.18);
          ctx.fillStyle = `rgba(${parts[0]},${parts[1]},${parts[2]},${alpha})`;
          ctx.fillRect(px(x0), py(y0), px(x1 - x0), py(y1 - y0));
        }
      }

      ctx.strokeStyle = C.paddock_border;
      ctx.lineWidth = 1;
      ctx.setLineDash([]);
      ctx.strokeRect(px(x0), py(y0), px(x1 - x0), py(y1 - y0));
    }

    // --- Paddock labels ---
    ctx.font = `${Math.round(W * 0.018)}px "JetBrains Mono Variable", monospace`;
    for (const p of paddocks) {
      const anchor = paddockLabelAnchor(p, px, py);
      ctx.textAlign = anchor.align;
      const label = p.id.toUpperCase();
      const metrics = ctx.measureText(label);
      const padX = 4;
      const padY = 3;
      const lw = metrics.width + padX * 2;
      const lh = Math.round(W * 0.018) + padY * 2;
      let bgX = anchor.x;
      if (anchor.align === "right") bgX = anchor.x - metrics.width - padX;
      else if (anchor.align === "center") bgX = anchor.x - metrics.width / 2 - padX;
      else bgX = anchor.x - padX;
      const bgY = anchor.y - Math.round(W * 0.018) - padY / 2;
      ctx.fillStyle = "rgba(10,12,16,0.6)";
      ctx.fillRect(bgX, bgY, lw, lh);
      ctx.fillStyle = C.text;
      ctx.fillText(label, anchor.x, anchor.y);

      const [x0, y0, x1, y1] = p.bounds;
      const forage = p.forage_pct ?? 60;
      const barW = px(x1 - x0) - 8;
      const barH = 2;
      const barY = py(y1) - barH - 3;
      const isBottomRow = y0 >= 0.5;
      if (!isBottomRow) {
        ctx.fillStyle = "rgba(38,45,58,0.6)";
        ctx.fillRect(px(x0) + 4, barY, barW, barH);
        ctx.fillStyle = forage > 60 ? C.cow_healthy : forage > 35 ? C.cow_watch : C.cow_sick;
        ctx.fillRect(px(x0) + 4, barY, barW * (forage / 100), barH);
      }
    }
    ctx.textAlign = "left";

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
      const cx = px(tx),
        cy = py(ty);

      const sq = r * 1.4;
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.strokeRect(cx - sq, cy - sq, sq * 2, sq * 2);

      const fillH = sq * 2 * (level / 100);
      ctx.fillStyle = hexToRgba(color, 0.25);
      ctx.fillRect(cx - sq, cy + sq - fillH, sq * 2, fillH);

      ctx.fillStyle = color;
      ctx.font = `${Math.round(W * 0.016)}px "JetBrains Mono Variable", monospace`;
      ctx.textAlign = "center";
      ctx.fillText(`TANK ${t.id.replace(/^tank_/i, "").toUpperCase()} ${Math.round(level)}%`, cx, cy + sq + 14);
      ctx.textAlign = "left";
    }

    // --- Cattle (with health ring, tween positions + fade-in + color blend) ---
    const cows: Cow[] = snap?.cows ?? [];
    const healthCounts = { healthy: 0, watch: 0, sick: 0, calving: 0 };
    for (const cow of cows) {
      const health = classifyCow(cow);
      healthCounts[health] += 1;
      const rec = state.cows.get(cow.id);
      // If a snapshot arrived via the prop path but the tween-apply hasn't
      // been called yet (defensive), fall back to the raw pos.
      const dispX = rec ? tweenValue(rec.xTween, nowMs) : cow.pos[0];
      const dispY = rec ? tweenValue(rec.yTween, nowMs) : cow.pos[1];
      const rgb = rec ? tweenCowColor(rec, nowMs) : COW_RGB[health];
      const fadeT = rec
        ? Math.min(1, (nowMs - rec.fadeStartMs) / COW_FADE_IN_MS)
        : 1;
      const r = Math.max(3, Math.round(W * 0.011));
      const ppx = px(dispX);
      const ppy = py(dispY);
      const rgbStr = `rgba(${Math.round(rgb[0])},${Math.round(rgb[1])},${Math.round(rgb[2])},`;

      // Health ring for non-healthy cows
      if (health !== "healthy") {
        ctx.beginPath();
        ctx.arc(ppx, ppy, r * 2.2, 0, Math.PI * 2);
        ctx.strokeStyle = `${rgbStr}${0.5 * fadeT})`;
        ctx.lineWidth = 1.2;
        ctx.stroke();
      }

      // Core dot
      ctx.beginPath();
      ctx.arc(ppx, ppy, r, 0, Math.PI * 2);
      ctx.fillStyle = `${rgbStr}${0.92 * fadeT})`;
      ctx.fill();

      // Tag label for non-healthy cows
      if (cow.tag && health !== "healthy") {
        ctx.font = `bold ${Math.round(W * 0.013)}px "JetBrains Mono Variable", monospace`;
        ctx.fillStyle = `${rgbStr}${1 * fadeT})`;
        ctx.textAlign = "left";
        ctx.fillText(cow.tag, ppx + r + 4, ppy + 3);
      }
    }

    // --- Drone: tweened position + trail with fade-in per point ---
    let droneX = 0.5;
    let droneY = 0.5;
    if (state.drone) {
      droneX = tweenValue(state.drone.xTween, nowMs);
      droneY = tweenValue(state.drone.yTween, nowMs);
    } else if (snap?.drone) {
      // Fallback if snapshot arrived but tween pipeline has no state.
      const d = snap.drone;
      if (Array.isArray(d.pos)) [droneX, droneY] = d.pos;
      else if (d.lat !== undefined && d.lon !== undefined) {
        droneX = Math.max(0.05, Math.min(0.95, (d.lon - -106.48) / 0.05 + 0.5));
        droneY = Math.max(0.05, Math.min(0.95, (d.lat - 34.1) / 0.05 + 0.5));
      }
    }

    const trail = state.trail;
    for (let i = 1; i < trail.length; i++) {
      const age = nowMs - trail[i].spawnMs;
      const fadeIn = Math.min(1, age / TRAIL_FADE_MS);
      const alpha = (i / trail.length) * 0.55 * fadeIn;
      ctx.beginPath();
      ctx.moveTo(px(trail[i - 1].x), py(trail[i - 1].y));
      ctx.lineTo(px(trail[i].x), py(trail[i].y));
      ctx.strokeStyle = `rgba(120,180,220,${alpha})`;
      ctx.lineWidth = 1.5 + (i / trail.length) * 0.8;
      ctx.stroke();
    }

    // Drone triangle
    const dSize = Math.max(7, Math.round(W * 0.022));
    const dx = px(droneX),
      dy = py(droneY);
    ctx.beginPath();
    ctx.moveTo(dx, dy - dSize);
    ctx.lineTo(dx + dSize * 0.65, dy + dSize * 0.55);
    ctx.lineTo(dx - dSize * 0.65, dy + dSize * 0.55);
    ctx.closePath();
    ctx.fillStyle = "rgba(120,180,220,0.9)";
    ctx.fill();
    ctx.strokeStyle = C.drone;
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Drone label
    const labelAnchor = droneLabelOffset(dx, dy, W, H);
    ctx.fillStyle = C.drone;
    ctx.font = `bold ${Math.round(W * 0.015)}px "JetBrains Mono Variable", monospace`;
    ctx.textAlign = labelAnchor.align;
    const droneText = "DRONE";
    const droneMetrics = ctx.measureText(droneText);
    const dPadX = 4;
    const dPadY = 2;
    let dBgX = labelAnchor.x;
    if (labelAnchor.align === "right") dBgX = labelAnchor.x - droneMetrics.width - dPadX;
    else dBgX = labelAnchor.x - dPadX;
    const dBgY = labelAnchor.y - Math.round(W * 0.015) - dPadY;
    ctx.fillStyle = "rgba(10,12,16,0.72)";
    ctx.fillRect(dBgX, dBgY, droneMetrics.width + dPadX * 2, Math.round(W * 0.015) + dPadY * 2 + 2);
    ctx.fillStyle = C.drone;
    ctx.fillText(droneText, labelAnchor.x, labelAnchor.y);
    ctx.textAlign = "left";

    // --- Predators (tweened position + fade-in) ---
    const predators: Predator[] = snap?.predators ?? [];
    for (const pred of predators) {
      const rec = state.predators.get(pred.id);
      const rx = rec ? tweenValue(rec.xTween, nowMs) : pred.pos[0];
      const ry = rec ? tweenValue(rec.yTween, nowMs) : pred.pos[1];
      const fadeT = rec
        ? Math.min(1, (nowMs - rec.fadeStartMs) / PREDATOR_FADE_MS)
        : 1;
      const xSize = Math.max(6, Math.round(W * 0.02));
      const ppx = px(rx),
        ppy = py(ry);

      const nowS = nowMs / 1000;
      let phase = rec?.phase;
      if (phase === undefined) {
        phase = predatorPhaseRef.current.get(pred.id);
        if (phase === undefined) {
          phase = Math.random();
          predatorPhaseRef.current.set(pred.id, phase);
        }
      }
      const reduceMotion = reduceMotionRef.current;
      const ringAlphaBase = reduceMotion
        ? 0.25
        : 0.1 + 0.2 * Math.abs(Math.sin(((nowS + phase) * Math.PI) / 1.8));
      ctx.beginPath();
      ctx.arc(ppx, ppy, xSize * 1.8, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(224,100,90,${ringAlphaBase * fadeT})`;
      ctx.lineWidth = 1;
      ctx.stroke();

      // X mark
      ctx.strokeStyle = lerpRgb(
        [224, 100, 90],
        [224, 100, 90],
        0,
        fadeT,
      );
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
      const speciesText = pred.species?.toUpperCase() ?? "PRED";
      ctx.font = `bold ${Math.round(W * 0.016)}px "JetBrains Mono Variable", monospace`;
      const specMetrics = ctx.measureText(speciesText);
      const sPad = 4;
      ctx.fillStyle = `rgba(10,12,16,${0.72 * fadeT})`;
      ctx.fillRect(
        ppx + xSize + 2,
        ppy - Math.round(W * 0.016),
        specMetrics.width + sPad * 2,
        Math.round(W * 0.016) + 4,
      );
      ctx.fillStyle = `rgba(224,100,90,${fadeT})`;
      ctx.fillText(speciesText, ppx + xSize + 2 + sPad, ppy + 2);
    }

    // --- Weather overlay ---
    const weather = snap?.weather;
    if (weather) {
      const overlayW = 210,
        overlayH = 22;
      ctx.fillStyle = "rgba(10,12,16,0.78)";
      ctx.fillRect(4, H - overlayH - 4, overlayW, overlayH);
      ctx.strokeStyle = "rgba(110,122,140,0.3)";
      ctx.strokeRect(4, H - overlayH - 4, overlayW, overlayH);
      ctx.fillStyle = C.text;
      ctx.font = `${Math.round(W * 0.015)}px "JetBrains Mono Variable", monospace`;
      ctx.fillText(
        `${weather.conditions?.toUpperCase() ?? ""} ${Math.round(weather.temp_f ?? 0)}°F ${Math.round(weather.wind_kt ?? 0)}kt`,
        10,
        H - 9,
      );
    }

    // --- Cattle legend ---
    const legendX = W - 4;
    const legendY = H - 4;
    const legendW = 188;
    const legendH = 22;
    ctx.fillStyle = "rgba(10,12,16,0.78)";
    ctx.fillRect(legendX - legendW, legendY - legendH, legendW, legendH);
    ctx.strokeStyle = "rgba(110,122,140,0.3)";
    ctx.strokeRect(legendX - legendW, legendY - legendH, legendW, legendH);
    ctx.font = `${Math.round(W * 0.014)}px "JetBrains Mono Variable", monospace`;
    let segX = legendX - legendW + 6;
    const segY = legendY - 7;
    const totalCows = cows.length;
    const dotR = 3;
    ctx.fillStyle = C.cow_healthy;
    ctx.beginPath();
    ctx.arc(segX + dotR, segY - 3, dotR, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = C.text;
    ctx.fillText(`${healthCounts.healthy}`, segX + dotR * 2 + 3, segY);
    segX += 28;
    ctx.fillStyle = C.cow_watch;
    ctx.beginPath();
    ctx.arc(segX + dotR, segY - 3, dotR, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = C.text;
    ctx.fillText(`${healthCounts.watch}`, segX + dotR * 2 + 3, segY);
    segX += 28;
    ctx.fillStyle = C.cow_sick;
    ctx.beginPath();
    ctx.arc(segX + dotR, segY - 3, dotR, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = C.text;
    ctx.fillText(`${healthCounts.sick}`, segX + dotR * 2 + 3, segY);
    segX += 28;
    ctx.fillStyle = C.cow_calving;
    ctx.beginPath();
    ctx.arc(segX + dotR, segY - 3, dotR, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = C.text;
    ctx.fillText(`${healthCounts.calving}`, segX + dotR * 2 + 3, segY);
    segX += 36;
    ctx.fillStyle = C.text_bright;
    ctx.fillText(`· ${totalCows} HEAD`, segX, segY);

    ctx.restore();
  }, []);

  // Single shared RAF loop — drives the 2D canvas. TerrainLayer runs its
  // own WebGL RAF loop (which exits early under reduced-motion); we keep
  // the 2D loop separate because it must re-render every frame for tweens.
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

  // Update reduced-motion pref in response to OS changes at runtime.
  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return undefined;
    }
    const mql = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onChange = () => {
      reduceMotionRef.current = mql.matches;
    };
    reduceMotionRef.current = mql.matches;
    mql.addEventListener?.("change", onChange);
    return () => {
      mql.removeEventListener?.("change", onChange);
    };
  }, []);

  // SSE subscription — world snapshot + scenario zone glow
  useEffect(() => {
    const sse = getSSE();
    const onSnap = (payload: WorldSnapshot) => {
      snapshotRef.current = payload;
      const nowMs =
        typeof performance !== "undefined" && typeof performance.now === "function"
          ? performance.now()
          : Date.now();
      applySnapshotToTweens(
        entityRef.current,
        payload,
        nowMs,
        reduceMotionRef.current,
      );
    };
    const onScenarioActive = (p: { name?: string }) => {
      scenarioZoneRef.current = scenarioToZone(p?.name);
    };
    const onScenarioEnded = () => {
      scenarioZoneRef.current = {};
    };
    sse.on("world.snapshot", onSnap);
    sse.on("scenario.active", onScenarioActive);
    sse.on("scenario.ended", onScenarioEnded);
    return () => {
      sse.off("world.snapshot", onSnap);
      sse.off("scenario.active", onScenarioActive);
      sse.off("scenario.ended", onScenarioEnded);
    };
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
    return () => {
      observer.disconnect();
      clearTimeout(timeout);
    };
  }, []);

  return (
    <div className="relative w-full h-full">
      <TerrainLayer />
      <canvas
        ref={canvasRef}
        className="w-full h-full block relative"
        style={{ imageRendering: "crisp-edges" }}
        aria-label="Ranch map showing cattle positions by health status, drone patrol path, water tanks, paddock boundaries, and predators"
        role="img"
        data-testid="ranch-map-canvas"
      />
      <ScenarioBreadcrumb />
    </div>
  );
}

// ---------------------------------------------------------------------------
// ScenarioBreadcrumb — unchanged SSE contract, pinned top-right of map
// ---------------------------------------------------------------------------

interface ScenarioActivePayload {
  name?: string;
  pass_idx?: number;
  speed?: number;
  started_at?: string;
}

export function ScenarioBreadcrumb() {
  const [active, setActive] = useState<ScenarioActivePayload | null>(null);
  const [now, setNow] = useState<number>(() => Date.now());

  useEffect(() => {
    const sse = getSSE();
    const onActive = (p: ScenarioActivePayload) => {
      if (p && typeof p.name === "string") setActive(p);
    };
    const onEnded = () => setActive(null);
    sse.on("scenario.active", onActive);
    sse.on("scenario.ended", onEnded);
    return () => {
      sse.off("scenario.active", onActive);
      sse.off("scenario.ended", onEnded);
    };
  }, []);

  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [active]);

  if (!active || !active.name) return null;

  let elapsedS = 0;
  if (active.started_at) {
    const started = Date.parse(active.started_at);
    if (!Number.isNaN(started)) {
      elapsedS = Math.max(0, Math.floor((now - started) / 1000));
    }
  }
  const mm = String(Math.floor(elapsedS / 60)).padStart(2, "0");
  const ss = String(elapsedS % 60).padStart(2, "0");

  return (
    <div
      data-testid="scenario-breadcrumb"
      className="chip chip-sage tabnum absolute top-2 right-2"
      style={{ pointerEvents: "none" }}
      aria-label={`Active scenario: ${active.name}`}
    >
      SCENARIO: {active.name.toUpperCase()} · {mm}:{ss}
    </div>
  );
}
