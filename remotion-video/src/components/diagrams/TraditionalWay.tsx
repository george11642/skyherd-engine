/**
 * TraditionalWay v4 — multi-method ranch + SkyHerd comparison beat (24s window).
 *
 * Total scene: 720 frames (24s @ 30fps).
 *
 * Phases:
 *   1. Setup            f0-80     title + ranch map fade in
 *   2. Multi-method     f80-480   helicopter, dogs, ATV, truck operating
 *                                 simultaneously across the ranch
 *   3. Missed events    f320-540  3 pulses (coyote/sick cow/empty tank)
 *                                 + "$12K / yr" cost callout
 *   4. SkyHerd overlay  f540-720  traditional methods dim, nervous-system
 *                                 overlay sweeps in (sensors + FOV + drone),
 *                                 ✗ flip to ✓, comparator card slides in
 *
 * Keeps the SVG ranch-shape skeleton from v2 (paddocks, troughs, road,
 * pen, house, compass). Truck loop math reused at 70% size; missed-event
 * pulse mechanism reused with new fire frames; clock simplified to a
 * smooth 11pm→midnight ramp.
 */
import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

// ─── Palette ─────────────────────────────────────────────────────────────────
const CREAM      = "rgb(245 240 230)";
const CREAM_DARK = "rgb(228 220 205)";
const SAGE       = "rgb(148 176 136)";
const SAGE_DARK  = "rgb(100 130 90)";
const TERRACOTTA = "rgb(188 90 60)";
const SKY        = "rgb(120 180 220)";
const INK        = "rgb(45 42 38)";
const INK_LIGHT  = "rgb(90 86 80)";
const DUST       = "rgb(178 156 122)";
const EMERALD    = "rgb(16 185 129)";    // SkyHerd nervous-system color
const EMERALD_DK = "rgb(5 150 105)";
const MONO       = "ui-monospace, 'JetBrains Mono', monospace";
const SERIF      = "Georgia, 'Times New Roman', serif";

// ─── Scene phase boundaries (frames) ─────────────────────────────────────────
// Total: 720 frames (24s @ 30fps).
//   0..80    Phase 1: title + map fade in
//   80..480  Phase 2: multi-method active (helicopter, dogs, ATV, truck)
//   320..540 Phase 3: missed-events pulse (overlaps phase 2 tail)
//   540..720 Phase 4: SkyHerd comparison beat (dim → overlay → comparator)
const MULTI_END        = 480;
const COMPARE_START    = 540;
const COMPARE_DIM_END  = 570;

// ─── Ranch shape (irregular polygon) ─────────────────────────────────────────
const RANCH_POLY = [
  [0.10, 0.20], // NW corner (offset west)
  [0.55, 0.15], // N-top gentle jog
  [0.88, 0.18], // NE
  [0.90, 0.55], // E mid
  [0.82, 0.82], // SE
  [0.45, 0.86], // S mid
  [0.12, 0.80], // SW
  [0.08, 0.48], // W mid
] as Array<[number, number]>;

function polyPoints(poly: Array<[number, number]>, w: number, h: number): string {
  return poly.map(([x, y]) => `${x * w},${y * h}`).join(" ");
}

// ─── Road waypoints (fraction coords, clockwise) ─────────────────────────────
const ROAD_WP: Array<[number, number]> = [
  [0.22, 0.28], // NW road start
  [0.50, 0.22], // N straight
  [0.78, 0.26], // NE
  [0.82, 0.50], // E side
  [0.72, 0.72], // SE swing (near tank)
  [0.48, 0.76], // S road
  [0.22, 0.72], // SW
  [0.15, 0.50], // W side
];

function lerpWp(wp: Array<[number, number]>, t: number): { x: number; y: number } {
  const n = wp.length;
  const segment = t * n;
  const i = Math.floor(segment) % n;
  const j = (i + 1) % n;
  const frac = segment - Math.floor(segment);
  return {
    x: wp[i][0] + (wp[j][0] - wp[i][0]) * frac,
    y: wp[i][1] + (wp[j][1] - wp[i][1]) * frac,
  };
}

function truckAngle(wp: Array<[number, number]>, t: number): number {
  const eps = 0.001;
  const a = lerpWp(wp, t);
  const b = lerpWp(wp, (t + eps) % 1);
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  return (Math.atan2(dy, dx) * 180) / Math.PI;
}

// Truck completes ~1.0 lap across the multi-method window (400f).
const LAP_FRAMES = 400;

// ─── Clock — smooth 11:00 PM → 12:00 AM (midnight) across f0-480 ─────────────
function clockText(frame: number): string {
  // 23:00 → 24:00 over 0..480 frames
  const totalMin = interpolate(frame, [0, MULTI_END], [23 * 60, 24 * 60], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const mins = Math.floor(totalMin);
  const h24 = Math.floor(mins / 60) % 24;
  const m = mins % 60;
  const period = h24 < 12 ? "AM" : "PM";
  const displayH = h24 % 12 === 0 ? 12 : h24 % 12;
  const mStr = m < 10 ? `0${m}` : `${m}`;
  return `${displayH}:${mStr} ${period}`;
}

// ─── Missed events — fire frames re-scoped for 720f scene ────────────────────
type MissedEvent = {
  label: "COYOTE" | "SICK COW" | "EMPTY TANK";
  shortLabel: string;
  fireFrame: number;
  flipFrame: number;
  x: number;
  y: number;
};

const EVENTS: MissedEvent[] = [
  { label: "COYOTE",     shortLabel: "Coyote at fence",  fireFrame: 320, flipFrame: 610, x: 0.74, y: 0.35 },
  { label: "SICK COW",   shortLabel: "Cow issue",        fireFrame: 400, flipFrame: 630, x: 0.28, y: 0.64 },
  { label: "EMPTY TANK", shortLabel: "Water shortage",   fireFrame: 480, flipFrame: 650, x: 0.70, y: 0.72 },
];

// ─── SkyHerd nervous-system overlay anchors ──────────────────────────────────
// 8 LoRaWAN sensor dots: 4 troughs + 2 fence corners + 2 mid-pasture
const LORA_DOTS: Array<{ x: number; y: number; reveal: number }> = [
  { x: 0.78, y: 0.245, reveal: 560 }, // trough 1 (NE)
  { x: 0.71, y: 0.715, reveal: 568 }, // trough 2 (south)
  { x: 0.32, y: 0.30,  reveal: 576 }, // mid-N pasture trough (implicit)
  { x: 0.55, y: 0.66,  reveal: 584 }, // mid-S pasture trough
  { x: 0.12, y: 0.20,  reveal: 592 }, // NW fence corner
  { x: 0.88, y: 0.18,  reveal: 600 }, // NE fence corner
  { x: 0.30, y: 0.40,  reveal: 608 }, // mid-N pasture
  { x: 0.62, y: 0.55,  reveal: 616 }, // mid-pasture S
];

// 3 camera FOV cones (translucent emerald arcs)
const CAMERAS: Array<{ x: number; y: number; angleDeg: number; reveal: number }> = [
  { x: 0.78, y: 0.78, angleDeg: 200, reveal: 570 }, // SE camera, looking NW into fields
  { x: 0.14, y: 0.22, angleDeg: 30,  reveal: 590 }, // NW camera, looking SE
  { x: 0.50, y: 0.18, angleDeg: 110, reveal: 610 }, // N camera, looking S
];

// 1 drone path: ranch house → coyote position
const DRONE_PATH = {
  start:  { x: 0.17, y: 0.50 },
  end:    { x: 0.74, y: 0.35 },
  reveal: 590,
};

// ─── Helicopter SVG silhouette ───────────────────────────────────────────────
type HelicopterProps = { x: number; y: number; rotation: number; rotor: number; opacity: number };
function Helicopter({ x, y, rotation, rotor, opacity }: HelicopterProps) {
  return (
    <g transform={`translate(${x},${y}) rotate(${rotation})`} opacity={opacity}>
      {/* Tail boom */}
      <rect x={-44} y={-3} width={36} height={6} rx={2} fill={SAGE_DARK} />
      {/* Tail rotor */}
      <circle cx={-44} cy={0} r={4} fill={SAGE_DARK} />
      <line x1={-44} y1={-7} x2={-44} y2={7} stroke={INK_LIGHT} strokeWidth={1.5} opacity={0.6} />
      {/* Body */}
      <ellipse cx={6} cy={0} rx={20} ry={10} fill={SAGE_DARK} />
      <ellipse cx={10} cy={-1} rx={9} ry={5} fill={SKY} opacity={0.6} />
      {/* Skid */}
      <line x1={-8} y1={11} x2={20} y2={11} stroke={INK} strokeWidth={1.5} />
      {/* Main rotor — 3 strokes spinning */}
      <g transform={`rotate(${rotor})`}>
        <line x1={-30} y1={0} x2={30} y2={0} stroke={INK} strokeWidth={2} opacity={0.55} />
      </g>
      <g transform={`rotate(${rotor + 60})`}>
        <line x1={-30} y1={0} x2={30} y2={0} stroke={INK} strokeWidth={2} opacity={0.45} />
      </g>
      <g transform={`rotate(${rotor + 120})`}>
        <line x1={-30} y1={0} x2={30} y2={0} stroke={INK} strokeWidth={2} opacity={0.35} />
      </g>
      {/* Hub */}
      <circle cx={6} cy={0} r={3} fill={INK} />
    </g>
  );
}

// ─── Working dog SVG silhouette ──────────────────────────────────────────────
type DogProps = { x: number; y: number; bounce: number; opacity: number; flip?: boolean };
function WorkingDog({ x, y, bounce, opacity, flip }: DogProps) {
  const sx = flip ? -1 : 1;
  return (
    <g transform={`translate(${x},${y - bounce}) scale(${sx},1)`} opacity={opacity}>
      {/* Body */}
      <ellipse cx={0} cy={0} rx={11} ry={5} fill={DUST} />
      {/* Head */}
      <circle cx={10} cy={-3} r={5} fill={DUST} />
      {/* Snout */}
      <ellipse cx={14} cy={-2} rx={3} ry={2} fill={INK_LIGHT} />
      {/* Ear */}
      <polygon points="8,-7 10,-10 12,-6" fill={INK_LIGHT} />
      {/* Tail */}
      <line x1={-10} y1={-1} x2={-15} y2={-5} stroke={DUST} strokeWidth={3} strokeLinecap="round" />
      {/* Front legs */}
      <line x1={6} y1={4} x2={6} y2={9} stroke={DUST} strokeWidth={2.5} strokeLinecap="round" />
      <line x1={9} y1={4} x2={9} y2={9} stroke={DUST} strokeWidth={2.5} strokeLinecap="round" />
      {/* Back legs */}
      <line x1={-5} y1={4} x2={-5} y2={9} stroke={DUST} strokeWidth={2.5} strokeLinecap="round" />
      <line x1={-8} y1={4} x2={-8} y2={9} stroke={DUST} strokeWidth={2.5} strokeLinecap="round" />
    </g>
  );
}

// ─── ATV SVG silhouette (side profile) ───────────────────────────────────────
type AtvProps = { x: number; y: number; wheelSpin: number; opacity: number; flip?: boolean };
function ATV({ x, y, wheelSpin, opacity, flip }: AtvProps) {
  const sx = flip ? -1 : 1;
  return (
    <g transform={`translate(${x},${y}) scale(${sx},1)`} opacity={opacity}>
      {/* Chassis */}
      <rect x={-14} y={-6} width={28} height={8} rx={2} fill={TERRACOTTA} />
      {/* Seat */}
      <rect x={-3} y={-11} width={10} height={5} rx={1.5} fill={INK} />
      {/* Handlebars */}
      <line x1={11} y1={-12} x2={14} y2={-7} stroke={INK} strokeWidth={2} strokeLinecap="round" />
      <line x1={14} y1={-13} x2={14} y2={-9} stroke={INK} strokeWidth={2} strokeLinecap="round" />
      {/* Headlight */}
      <circle cx={15} cy={-3} r={2} fill="rgb(255 220 120)" />
      {/* Wheels (with rotation marks) */}
      <g transform={`translate(-10,4)`}>
        <circle r={6} fill={INK} />
        <line
          x1={0} y1={0}
          x2={6 * Math.cos(wheelSpin)} y2={6 * Math.sin(wheelSpin)}
          stroke={INK_LIGHT} strokeWidth={1.5}
        />
      </g>
      <g transform={`translate(10,4)`}>
        <circle r={6} fill={INK} />
        <line
          x1={0} y1={0}
          x2={6 * Math.cos(wheelSpin)} y2={6 * Math.sin(wheelSpin)}
          stroke={INK_LIGHT} strokeWidth={1.5}
        />
      </g>
    </g>
  );
}

// ─── Camera FOV cone (30deg arc) ─────────────────────────────────────────────
type FovProps = { cx: number; cy: number; angleDeg: number; radius: number; opacity: number };
function FovCone({ cx, cy, angleDeg, radius, opacity }: FovProps) {
  const half = 15; // half-angle in degrees → 30deg cone
  const a1 = ((angleDeg - half) * Math.PI) / 180;
  const a2 = ((angleDeg + half) * Math.PI) / 180;
  const x1 = cx + radius * Math.cos(a1);
  const y1 = cy + radius * Math.sin(a1);
  const x2 = cx + radius * Math.cos(a2);
  const y2 = cy + radius * Math.sin(a2);
  const path = `M ${cx},${cy} L ${x1},${y1} A ${radius},${radius} 0 0 1 ${x2},${y2} Z`;
  return (
    <g opacity={opacity}>
      <path d={path} fill={EMERALD} fillOpacity={0.18} stroke={EMERALD} strokeWidth={1.5} />
      <circle cx={cx} cy={cy} r={4} fill={EMERALD_DK} />
    </g>
  );
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
function clamp01(t: number): number {
  return Math.max(0, Math.min(1, t));
}

export const TraditionalWay: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  // ── Phase 1: Title + map fade in (0..80) ───────────────────────────────────
  const setupOp = interpolate(frame, [0, 40], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // ── Phase 4: Traditional methods dim during compare beat ───────────────────
  // Fade traditional actors + missed-event icons from 1.0 → 0.25 over 540..570
  const traditionalOp = interpolate(
    frame,
    [COMPARE_START, COMPARE_DIM_END],
    [1, 0.25],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  // ── Truck — slow road loop (only animates while in the multi-method beat) ──
  // Truck stops at MULTI_END so it doesn't overlap with the comparison beat.
  const truckActiveFrame = Math.min(frame, MULTI_END);
  const lapT = (truckActiveFrame % LAP_FRAMES) / LAP_FRAMES;
  const truck = lerpWp(ROAD_WP, lapT);
  const tAngle = truckAngle(ROAD_WP, lapT);

  // ── Helicopter — wide circular orbit around N pasture, ~1.5 laps in 480f ──
  // Center: NE of north pasture. Slight tilt with motion direction.
  const heliCenter = { x: 0.50 * width, y: 0.32 * height };
  const heliRadiusX = 0.30 * width;
  const heliRadiusY = 0.16 * height;
  // Phase: 1.5 laps from f0..f480 (active multi-method window).
  const heliPhase = (Math.min(frame, MULTI_END) / MULTI_END) * Math.PI * 3;
  const heliX = heliCenter.x + heliRadiusX * Math.cos(heliPhase);
  const heliY = heliCenter.y + heliRadiusY * Math.sin(heliPhase);
  // Tangent angle for nose direction
  const heliTangent =
    (Math.atan2(heliRadiusY * Math.cos(heliPhase), -heliRadiusX * Math.sin(heliPhase)) * 180) /
    Math.PI;
  const heliTilt = Math.sin(heliPhase) * 6; // slight banking
  // Rotor spin (degrees) — fast spin
  const rotorAngle = (frame * 28) % 360;
  // During the comparison beat the helicopter also slows + dims.
  const heliCompareDrift = Math.sin(((frame - COMPARE_START) / 30) * Math.PI * 0.5) * 4;
  const heliFinalX = frame >= COMPARE_START ? heliX + heliCompareDrift : heliX;

  // ── Working dogs — bounce alongside truck on the road loop ─────────────────
  // Two dogs offset from truck position, bouncing slightly out of phase.
  // Dog 1 leads truck by ~4% of lap; Dog 2 trails by ~4%.
  const dog1T = (lapT + 0.04) % 1;
  const dog2T = (lapT - 0.04 + 1) % 1;
  const dog1Pos = lerpWp(ROAD_WP, dog1T);
  const dog2Pos = lerpWp(ROAD_WP, dog2T);
  const dog1Bounce = Math.abs(Math.sin((frame * Math.PI) / 6)) * 4;
  const dog2Bounce = Math.abs(Math.sin((frame * Math.PI) / 6 + Math.PI / 3)) * 4;

  // Dog 1 sprint: at f240, dog 1 sprints toward the COYOTE marker, returns.
  // Sprint window: f240..f320 (80f). Linear interp from dog1Pos -> coyote -> back.
  const sprintT = clamp01((frame - 240) / 80);
  // 0 → 0.5 outbound, 0.5 → 1.0 return.
  const sprintPhase = sprintT < 0.5 ? sprintT * 2 : (1 - sprintT) * 2;
  const coyoteX = EVENTS[0].x;
  const coyoteY = EVENTS[0].y;
  const sprintActive = frame >= 240 && frame <= 320;
  const dog1FinalX = sprintActive
    ? dog1Pos.x + (coyoteX - dog1Pos.x) * sprintPhase
    : dog1Pos.x;
  const dog1FinalY = sprintActive
    ? dog1Pos.y + (coyoteY - dog1Pos.y) * sprintPhase
    : dog1Pos.y;

  // ── ATV — linear traverse along east fence, takes 320f to cross ────────────
  // East fence runs from ~(0.86, 0.20) to ~(0.86, 0.80).
  // ATV active f80..f400 (320f window).
  const atvT = clamp01((frame - 80) / 320);
  const atvX = 0.86;
  const atvY = 0.20 + (0.80 - 0.20) * atvT;
  const atvOp = interpolate(frame, [80, 100, 400, 420], [0, 1, 1, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  // Wheel spin (radians)
  const atvWheelSpin = (frame * 0.6) % (Math.PI * 2);

  // ── Sub-label fade in at f160 ──────────────────────────────────────────────
  const subLabelOp = interpolate(frame, [160, 200], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  // Sub-label also dims during compare beat.
  const subLabelCompareOp = interpolate(
    frame,
    [COMPARE_START, COMPARE_DIM_END],
    [1, 0.25],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  // ── Clock visible during phase 2-3, fades during compare ───────────────────
  const clock = clockText(frame);
  const clockOp = interpolate(
    frame,
    [0, 40, COMPARE_START, COMPARE_DIM_END],
    [0, 1, 1, 0.3],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  // ── $12K cost callout: fires f490 (aligned with EMPTY TANK pulse) ──────────
  const costOp = interpolate(
    frame,
    [490, 508, 540, 560],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  // ── Comparator card slide-in (right edge, frames 600..640) ─────────────────
  const comparatorBaseOp = interpolate(frame, [600, 640], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: CREAM, opacity: setupOp }}>
      {/* ── Title ── */}
      <div
        style={{
          position: "absolute",
          top: 36,
          left: 0,
          right: 0,
          textAlign: "center",
          fontFamily: SERIF,
          fontWeight: 700,
          fontSize: 42,
          color: INK,
          letterSpacing: "-0.01em",
        }}
      >
        How a Ranch Runs Today
      </div>

      {/* ── Ranch map SVG (always at full opacity — base layer) ── */}
      <svg
        style={{ position: "absolute", inset: 0 }}
        viewBox={`0 0 ${width} ${height}`}
        width={width}
        height={height}
      >
        {/* Ranch boundary — irregular polygon */}
        <polygon
          points={polyPoints(RANCH_POLY, width, height)}
          fill={CREAM_DARK}
          stroke={SAGE_DARK}
          strokeWidth={3}
        />

        {/* Fence tick marks along north boundary */}
        {[...Array(16)].map((_, i) => {
          const x1 = width * 0.10 + i * (width * 0.78 / 15);
          return (
            <line
              key={`ft-${i}`}
              x1={x1} y1={height * 0.17}
              x2={x1} y2={height * 0.17 + 14}
              stroke={SAGE_DARK} strokeWidth={2}
            />
          );
        })}

        {/* Road loop — dashed path through waypoints */}
        <polyline
          points={[...ROAD_WP, ROAD_WP[0]].map(([x, y]) => `${x * width},${y * height}`).join(" ")}
          fill="none"
          stroke={SAGE}
          strokeWidth={4}
          strokeDasharray="18 10"
          opacity={0.7}
        />

        {/* Paddock 1 — NW pasture */}
        <polygon
          points={`
            ${width * 0.14},${height * 0.25}
            ${width * 0.40},${height * 0.22}
            ${width * 0.42},${height * 0.48}
            ${width * 0.16},${height * 0.50}
          `}
          fill="rgb(148 176 136 / 0.22)"
          stroke={SAGE}
          strokeWidth={1.5}
        />
        <text
          x={width * 0.26} y={height * 0.37}
          textAnchor="middle"
          fontFamily={MONO}
          fontSize={13}
          fill={SAGE_DARK}
          opacity={0.75}
        >NORTH PASTURE</text>

        {/* Paddock 2 — SE pasture */}
        <polygon
          points={`
            ${width * 0.45},${height * 0.55}
            ${width * 0.78},${height * 0.52}
            ${width * 0.76},${height * 0.78}
            ${width * 0.44},${height * 0.80}
          `}
          fill="rgb(148 176 136 / 0.22)"
          stroke={SAGE}
          strokeWidth={1.5}
        />
        <text
          x={width * 0.60} y={height * 0.68}
          textAnchor="middle"
          fontFamily={MONO}
          fontSize={13}
          fill={SAGE_DARK}
          opacity={0.75}
        >SOUTH PASTURE</text>

        {/* Holding pen — mid-left */}
        <rect
          x={width * 0.18} y={height * 0.58}
          width={width * 0.10} height={height * 0.10}
          rx={4}
          fill="rgb(210 178 138 / 0.40)"
          stroke="rgb(180 140 80)"
          strokeWidth={1.5}
        />
        <text
          x={width * 0.23} y={height * 0.66}
          textAnchor="middle"
          fontFamily={MONO}
          fontSize={11}
          fill="rgb(140 100 50)"
          opacity={0.85}
        >PEN</text>

        {/* Water trough 1 — NE */}
        <rect x={width * 0.75} y={height * 0.23} width={22} height={12} rx={3}
          fill={SKY} opacity={0.75} />
        <text x={width * 0.78} y={height * 0.22}
          textAnchor="middle" fontFamily={MONO} fontSize={11} fill={SKY} opacity={0.8}>
          TROUGH 1
        </text>

        {/* Water trough 2 — south (the one that goes empty) */}
        <rect x={width * 0.67} y={height * 0.69} width={22} height={12} rx={3}
          fill={SKY} opacity={0.75} />
        <text x={width * 0.70} y={height * 0.68}
          textAnchor="middle" fontFamily={MONO} fontSize={11} fill={SKY} opacity={0.8}>
          TROUGH 2
        </text>

        {/* Ranch house marker — SW */}
        <polygon
          points={`
            ${width * 0.14},${height * 0.50}
            ${width * 0.17},${height * 0.46}
            ${width * 0.20},${height * 0.50}
          `}
          fill={TERRACOTTA} opacity={0.6}
        />
        <rect x={width * 0.14} y={height * 0.50} width={width * 0.06} height={height * 0.05}
          fill={TERRACOTTA} opacity={0.4} />
        <text x={width * 0.17} y={height * 0.58}
          textAnchor="middle" fontFamily={MONO} fontSize={10} fill={TERRACOTTA} opacity={0.85}>
          HOUSE
        </text>

        {/* Compass rose — top-right corner of map */}
        <text x={width * 0.86} y={height * 0.22}
          textAnchor="middle" fontFamily={MONO} fontSize={13} fill={INK_LIGHT} opacity={0.55}
          fontWeight="700">N↑</text>

        {/* ── Traditional actors layer (helicopter, dogs, ATV) ── */}
        <g opacity={traditionalOp}>
          {/* ATV dust trail — short trailing line behind ATV */}
          {frame >= 80 && frame <= 420 && (
            <line
              x1={atvX * width - 18}
              y1={atvY * height + 4}
              x2={atvX * width - 4}
              y2={atvY * height + 4}
              stroke={DUST}
              strokeWidth={2}
              strokeLinecap="round"
              opacity={0.55}
            />
          )}

          {/* ATV */}
          <ATV
            x={atvX * width}
            y={atvY * height}
            wheelSpin={atvWheelSpin}
            opacity={atvOp}
          />

          {/* Working dog 1 (with optional sprint to coyote) */}
          <WorkingDog
            x={dog1FinalX * width}
            y={dog1FinalY * height}
            bounce={dog1Bounce}
            opacity={1}
            flip={false}
          />
          {/* Working dog 2 (always with truck) */}
          <WorkingDog
            x={dog2Pos.x * width}
            y={dog2Pos.y * height}
            bounce={dog2Bounce}
            opacity={1}
            flip
          />

          {/* Helicopter — orbiting north pasture */}
          <Helicopter
            x={heliFinalX}
            y={heliY}
            rotation={heliTangent + heliTilt}
            rotor={rotorAngle}
            opacity={1}
          />
        </g>
      </svg>

      {/* ── Truck emoji (scaled to 70% — was 30px, now 21px-equivalent via scale) ── */}
      <div
        style={{
          position: "absolute",
          left: truck.x * width - 14,
          top: truck.y * height - 13,
          fontSize: 21,
          transform: `rotate(${tAngle}deg)`,
          filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.28))",
          lineHeight: 1,
          zIndex: 10,
          opacity: traditionalOp,
        }}
      >
        🚛
      </div>

      {/* ── Missed event icons at FIXED positions ── */}
      {EVENTS.map((ev) => {
        const pulseAge = frame - ev.fireFrame;
        const hasStarted = pulseAge >= 0;
        const isRinging = hasStarted && pulseAge < 40;
        const pulseScale = isRinging
          ? interpolate(pulseAge, [0, 10, 25, 40], [0.7, 1.4, 1.1, 1.0], {
              extrapolateLeft: "clamp", extrapolateRight: "clamp",
            })
          : 1;
        const ringOp = isRinging
          ? interpolate(pulseAge, [0, 20, 40], [0, 0.95, 0], {
              extrapolateLeft: "clamp", extrapolateRight: "clamp",
            })
          : 0;
        const iconOp = hasStarted ? 1 : 0.18;
        // Has the SkyHerd nervous-system reached this event yet?
        const flipped = frame >= ev.flipFrame;
        // Fade red-ring color toward emerald during flip transition.
        const flipT = clamp01((frame - ev.flipFrame) / 20);
        const labelColor = flipped
          ? interpolateColor(TERRACOTTA, EMERALD_DK, flipT)
          : hasStarted
            ? TERRACOTTA
            : SAGE_DARK;

        // Spring pop-in on first appearance
        const popSp = spring({
          frame: ev.fireFrame > 0 ? frame - ev.fireFrame : frame,
          fps,
          config: { damping: 80, stiffness: 280 },
        });
        const popScale = hasStarted ? interpolate(popSp, [0, 1], [0, 1], {
          extrapolateLeft: "clamp", extrapolateRight: "clamp",
        }) : 1;

        // Ring color shifts to emerald after flip.
        const ringColor = flipped ? EMERALD : TERRACOTTA;

        // During compare beat, the icon dims along with traditional layer
        // EXCEPT for the symbol itself — which stays at full opacity to show ✗→✓.
        const containerDim =
          frame >= COMPARE_START
            ? interpolate(frame, [COMPARE_START, COMPARE_DIM_END], [1, 0.85], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              })
            : 1;

        return (
          <div
            key={ev.label}
            style={{
              position: "absolute",
              left: ev.x * width - 36,
              top: ev.y * height - 36,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 5,
              zIndex: 20,
              opacity: containerDim,
            }}
          >
            {/* Expanding pulse ring */}
            <div style={{
              position: "absolute",
              width: 72,
              height: 72,
              borderRadius: "50%",
              border: `3px solid ${ringColor}`,
              opacity: ringOp,
              transform: `scale(${pulseScale * 1.25})`,
              top: -4,
              left: -4,
            }} />
            {/* Second, slower ring */}
            <div style={{
              position: "absolute",
              width: 72,
              height: 72,
              borderRadius: "50%",
              border: `2px solid ${ringColor}`,
              opacity: ringOp * 0.55,
              transform: `scale(${pulseScale * 1.8})`,
              top: -4,
              left: -4,
            }} />

            {/* Icon */}
            <div style={{
              fontSize: 32,
              opacity: iconOp,
              transform: `scale(${hasStarted ? pulseScale * popScale : 1})`,
              filter: isRinging ? `drop-shadow(0 0 10px ${ringColor})` : "none",
              lineHeight: 1,
            }}>
              {ev.label === "COYOTE" ? "🐺" : ev.label === "SICK COW" ? "🐄" : "💧"}
            </div>

            {/* Label — flips between MISSED and shortLabel */}
            <div style={{
              fontFamily: MONO,
              fontSize: 11,
              color: labelColor,
              fontWeight: 800,
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              whiteSpace: "nowrap",
              opacity: iconOp,
            }}>
              {flipped ? "ON IT" : hasStarted ? "MISSED" : ev.label}
            </div>

            {/* Sub-label (description, only after fire) */}
            {hasStarted && (
              <div style={{
                fontFamily: MONO,
                fontSize: 10,
                color: flipped ? EMERALD_DK : TERRACOTTA,
                opacity: 0.85,
                letterSpacing: "0.06em",
              }}>
                {ev.shortLabel}
              </div>
            )}

            {/* ✗ → ✓ flip badge */}
            {hasStarted && (
              <div style={{
                position: "absolute",
                top: -16,
                right: -22,
                fontFamily: MONO,
                fontSize: 22,
                fontWeight: 900,
                color: flipped ? EMERALD_DK : TERRACOTTA,
                transition: "color 0.2s",
                textShadow: `0 0 6px ${flipped ? "rgba(16,185,129,0.5)" : "rgba(188,90,60,0.5)"}`,
                transform: `scale(${flipped
                  ? interpolate(flipT, [0, 0.6, 1], [1.4, 0.95, 1], {
                      extrapolateLeft: "clamp",
                      extrapolateRight: "clamp",
                    })
                  : 1})`,
              }}>
                {flipped ? "✓" : "✗"}
              </div>
            )}
          </div>
        );
      })}

      {/* ── Full-map red vignette on each event pulse ── */}
      {EVENTS.map((ev) => {
        const age = frame - ev.fireFrame;
        const vOp = age >= 0 && age < 25
          ? interpolate(age, [0, 6, 25], [0, 0.18, 0], {
              extrapolateLeft: "clamp", extrapolateRight: "clamp",
            })
          : 0;
        return (
          <div key={`v-${ev.label}`} style={{
            position: "absolute",
            inset: 0,
            backgroundColor: TERRACOTTA,
            opacity: vOp * (frame < COMPARE_START ? 1 : 0),
            pointerEvents: "none",
            zIndex: 15,
          }} />
        );
      })}

      {/* ── SkyHerd nervous-system overlay (frames 560..720) ── */}
      <svg
        style={{ position: "absolute", inset: 0, pointerEvents: "none", zIndex: 18 }}
        viewBox={`0 0 ${width} ${height}`}
        width={width}
        height={height}
      >
        {/* Camera FOV cones */}
        {CAMERAS.map((cam, i) => {
          const op = interpolate(frame, [cam.reveal, cam.reveal + 30], [0, 0.85], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return (
            <FovCone
              key={`fov-${i}`}
              cx={cam.x * width}
              cy={cam.y * height}
              angleDeg={cam.angleDeg}
              radius={Math.min(width, height) * 0.18}
              opacity={op}
            />
          );
        })}

        {/* Drone path: dashed arc from house → coyote */}
        {(() => {
          const pathOp = interpolate(
            frame,
            [DRONE_PATH.reveal, DRONE_PATH.reveal + 40],
            [0, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
          );
          const sx = DRONE_PATH.start.x * width;
          const sy = DRONE_PATH.start.y * height;
          const ex = DRONE_PATH.end.x * width;
          const ey = DRONE_PATH.end.y * height;
          // Arc control point (bowed up)
          const cx = (sx + ex) / 2;
          const cy = Math.min(sy, ey) - 60;
          const arcPath = `M ${sx},${sy} Q ${cx},${cy} ${ex},${ey}`;
          // Dash offset for "drawing" effect
          const lineLen = Math.hypot(ex - sx, ey - sy) * 1.25;
          const drawT = interpolate(
            frame,
            [DRONE_PATH.reveal, DRONE_PATH.reveal + 60],
            [0, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
          );
          return (
            <g opacity={pathOp}>
              <path
                d={arcPath}
                fill="none"
                stroke={EMERALD}
                strokeWidth={2.5}
                strokeDasharray={`${lineLen * drawT} ${lineLen}`}
                strokeLinecap="round"
              />
              {/* Drone dot at end */}
              {drawT > 0.9 && (
                <circle
                  cx={ex}
                  cy={ey}
                  r={5}
                  fill={EMERALD}
                  opacity={0.9}
                />
              )}
            </g>
          );
        })()}

        {/* LoRaWAN sensor dots */}
        {LORA_DOTS.map((dot, i) => {
          const op = interpolate(frame, [dot.reveal, dot.reveal + 14], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          // Pulsing inner halo
          const pulseSize = 1 + 0.3 * Math.sin(((frame - dot.reveal) * Math.PI) / 18);
          return (
            <g key={`lora-${i}`} opacity={op}>
              <circle
                cx={dot.x * width}
                cy={dot.y * height}
                r={10 * pulseSize}
                fill={EMERALD}
                opacity={0.18}
              />
              <circle
                cx={dot.x * width}
                cy={dot.y * height}
                r={6}
                fill={EMERALD_DK}
                stroke={CREAM}
                strokeWidth={1.5}
              />
            </g>
          );
        })}
      </svg>

      {/* ── Clock ── */}
      <div
        style={{
          position: "absolute",
          top: 60,
          right: 72,
          backgroundColor: "rgba(45,42,38,0.90)",
          borderRadius: 12,
          padding: "10px 20px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 3,
          zIndex: 30,
          opacity: clockOp,
        }}
      >
        <div style={{
          fontFamily: MONO,
          fontSize: 11,
          color: SAGE,
          letterSpacing: "0.22em",
          textTransform: "uppercase",
        }}>RANCH TIME</div>
        <div style={{
          fontFamily: MONO,
          fontSize: 32,
          color: CREAM,
          fontWeight: 700,
          letterSpacing: "0.04em",
        }}>
          {clock}
        </div>
      </div>

      {/* ── Sub-label ── */}
      <div
        style={{
          position: "absolute",
          bottom: 80,
          left: 0,
          right: 0,
          textAlign: "center",
          fontFamily: MONO,
          fontSize: 17,
          color: SAGE_DARK,
          letterSpacing: "0.14em",
          textTransform: "uppercase",
          opacity: subLabelOp * subLabelCompareOp,
          zIndex: 30,
        }}
      >
        Helicopters · Dogs · ATVs · Trucks — still missing things between runs
      </div>

      {/* ── "$12K / yr lost" cost callout (frames 330..400) ── */}
      <div
        style={{
          position: "absolute",
          bottom: 36,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          gap: 32,
          opacity: costOp,
          zIndex: 30,
        }}
      >
        <div style={{
          fontFamily: SERIF,
          fontSize: 36,
          fontWeight: 700,
          color: TERRACOTTA,
          letterSpacing: "-0.01em",
        }}>
          All missed.
        </div>
        <div style={{
          fontFamily: MONO,
          fontSize: 22,
          color: INK,
          backgroundColor: "rgba(188,90,60,0.12)",
          border: `2px solid ${TERRACOTTA}`,
          borderRadius: 8,
          padding: "8px 20px",
          letterSpacing: "0.06em",
          fontWeight: 700,
        }}>
          ~$12K / yr in lost events
        </div>
      </div>

      {/* ── Comparator card (right edge, frames 600..720) ── */}
      <ComparatorCard
        baseOp={comparatorBaseOp}
        frame={frame}
        height={height}
      />
    </AbsoluteFill>
  );
};

// ─── Comparator card component ───────────────────────────────────────────────
type ComparatorCardProps = { baseOp: number; frame: number; height: number };

type ComparatorKind = "traditional" | "skyherd" | "savings";

type ComparatorLine = {
  kind: ComparatorKind;
  label: string;
  price: string;
  detail: string;
  delay: number;
};

const COMPARATOR_LINES: Array<ComparatorLine> = [
  { kind: "traditional", label: "Helicopter",   price: "~$40,000 / yr",  detail: "skies clear",          delay: 0  },
  { kind: "traditional", label: "Working dogs", price: "~$6,000 / yr",   detail: "daylight only",        delay: 10 },
  { kind: "traditional", label: "ATV / truck",  price: "~$18,000 / yr",  detail: "between runs only",    delay: 20 },
  { kind: "traditional", label: "Lost events",  price: "~$12,000 / yr",  detail: "missed between runs",  delay: 30 },
  { kind: "skyherd",     label: "SkyHerd",      price: "$1,000 / month", detail: "24/7 · 10,000 acres · 500 head", delay: 50 },
  { kind: "savings",     label: "~$65,000 / yr saved", price: "",        detail: "",                     delay: 70 },
];

function ComparatorCard({ baseOp, frame, height }: ComparatorCardProps) {
  const slideStart = 600;
  return (
    <div
      style={{
        position: "absolute",
        right: 60,
        top: height * 0.22,
        width: "38%",
        maxWidth: 600,
        opacity: baseOp,
        zIndex: 40,
        fontFamily: MONO,
      }}
    >
      <div
        style={{
          backgroundColor: "rgba(245,240,230,0.96)",
          border: `2px solid ${INK_LIGHT}`,
          borderRadius: 14,
          padding: "22px 26px",
          boxShadow: "0 12px 28px rgba(45,42,38,0.18)",
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        <div
          style={{
            fontFamily: SERIF,
            fontSize: 18,
            fontWeight: 700,
            color: INK_LIGHT,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            paddingBottom: 8,
            borderBottom: `1px dashed ${SAGE_DARK}`,
          }}
        >
          The same job, compared
        </div>
        {COMPARATOR_LINES.map((line, i) => {
          const lineStart = slideStart + line.delay;
          const lineOp = interpolate(frame, [lineStart, lineStart + 12], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          const lineY = interpolate(frame, [lineStart, lineStart + 12], [12, 0], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          // Dashed dividers ABOVE the SkyHerd row (i=4) and ABOVE the savings row (i=5).
          const showTopDivider = line.kind === "skyherd" || line.kind === "savings";

          if (line.kind === "savings") {
            return (
              <div
                key={i}
                style={{
                  opacity: lineOp,
                  transform: `translateY(${lineY}px)`,
                  paddingTop: 12,
                  marginTop: 4,
                  borderTop: `1px dashed ${SAGE_DARK}`,
                  textAlign: "left",
                }}
              >
                <div
                  style={{
                    fontSize: 26,
                    fontWeight: 800,
                    color: EMERALD_DK,
                    letterSpacing: "0.03em",
                  }}
                >
                  {line.label}
                </div>
              </div>
            );
          }

          const isEmerald = line.kind === "skyherd";
          const labelColor = isEmerald ? EMERALD_DK : DUST;
          const priceColor = isEmerald ? EMERALD_DK : INK_LIGHT;
          const detailColor = isEmerald ? EMERALD_DK : SAGE_DARK;
          return (
            <div
              key={i}
              style={{
                opacity: lineOp,
                transform: `translateY(${lineY}px)`,
                display: "flex",
                flexDirection: "row",
                justifyContent: "space-between",
                alignItems: "baseline",
                gap: 12,
                paddingTop: showTopDivider ? 10 : 0,
                borderTop: showTopDivider ? `1px dashed ${SAGE_DARK}` : "none",
                marginTop: showTopDivider ? 4 : 0,
              }}
            >
              {/* Left col: label + detail */}
              <div style={{ display: "flex", flexDirection: "column", gap: 2, flex: "1 1 auto" }}>
                <div
                  style={{
                    fontSize: isEmerald ? 21 : 16,
                    fontWeight: isEmerald ? 800 : 700,
                    color: labelColor,
                    letterSpacing: "0.04em",
                  }}
                >
                  {line.label}
                </div>
                <div
                  style={{
                    fontSize: isEmerald ? 13 : 12,
                    color: detailColor,
                    letterSpacing: "0.02em",
                    fontWeight: isEmerald ? 600 : 400,
                  }}
                >
                  {line.detail}
                </div>
              </div>
              {/* Right col: price */}
              <div
                style={{
                  fontSize: isEmerald ? 18 : 14,
                  fontWeight: isEmerald ? 800 : 700,
                  color: priceColor,
                  letterSpacing: "0.02em",
                  whiteSpace: "nowrap",
                  textAlign: "right",
                }}
              >
                {line.price}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Color interp helper ─────────────────────────────────────────────────────
function parseRgb(rgb: string): [number, number, number] {
  // "rgb(188 90 60)" → [188,90,60]
  const m = rgb.match(/rgb\((\d+)\s+(\d+)\s+(\d+)\)/);
  if (!m) return [0, 0, 0];
  return [Number(m[1]), Number(m[2]), Number(m[3])];
}

function interpolateColor(a: string, b: string, t: number): string {
  const [r1, g1, b1] = parseRgb(a);
  const [r2, g2, b2] = parseRgb(b);
  const tt = clamp01(t);
  const r = Math.round(r1 + (r2 - r1) * tt);
  const g = Math.round(g1 + (g2 - g1) * tt);
  const bb = Math.round(b1 + (b2 - b1) * tt);
  return `rgb(${r} ${g} ${bb})`;
}
