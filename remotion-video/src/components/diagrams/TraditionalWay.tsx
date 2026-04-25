/**
 * TraditionalWay v2 — Scene 0:18–0:35 (17s / 510 frames @ 30fps)
 *
 * Real ranch-shape map with labelled paddocks and water sources.
 * Truck moves on a believable physical road loop, realistic pace.
 * 3 missed-event icons at FIXED positions (coyote south fence,
 * sick cow near pen, water tank far corner).
 * Events fire at VO words: "coyote" ~f285, "sick cow" ~f345, "tank" ~f405.
 * Time-of-day clock prominent in corner.
 * "$12K / yr in missed events" callout on the "All missed." beat.
 */
import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

const CREAM      = "rgb(245 240 230)";
const CREAM_DARK = "rgb(228 220 205)";
const SAGE       = "rgb(148 176 136)";
const SAGE_DARK  = "rgb(100 130 90)";
const TERRACOTTA = "rgb(188 90 60)";
const SKY        = "rgb(120 180 220)";
const INK        = "rgb(45 42 38)";
const INK_LIGHT  = "rgb(90 86 80)";
const MONO       = "ui-monospace, 'JetBrains Mono', monospace";
const SERIF      = "Georgia, 'Times New Roman', serif";

// ─── Ranch shape (irregular polygon) ────────────────────────────────────────
// Defined as fractions of (width, height). Mimics an NM-style irregular parcel.
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

// ─── Road waypoints (fraction coords, clockwise) ────────────────────────────
// A loop that stays ~0.1–0.15 inside the boundary, dips south, passes the pen.
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

// Lap time = 18 real seconds at 30fps → 540 frames; truck completes ~0.95 lap
const LAP_FRAMES = 540;

// ─── Clock that jumps to specific times ─────────────────────────────────────
// Maps frame → displayed time so events look contextual.
// f0→f240: 11:00 PM → 2:59 AM  (fast tick through night)
// f285: 3:00 AM (coyote)
// f285→f330: holds at 3:00 AM
// f345: 12:00 PM (sick cow)
// f405: 12:00 AM (tank)
function clockText(frame: number): string {
  let h: number, m: number;
  if (frame < 280) {
    // Ramp from 23:00 → 02:59 over first 280 frames
    const mins = Math.floor(interpolate(frame, [0, 280], [23 * 60, 2 * 60 + 59], {
      extrapolateLeft: "clamp", extrapolateRight: "clamp",
    }));
    h = Math.floor(mins / 60) % 24;
    m = mins % 60;
  } else if (frame < 340) {
    h = 3; m = 0; // coyote beat
  } else if (frame < 400) {
    h = 12; m = 0; // sick cow
  } else {
    h = 0; m = 0; // midnight
  }
  const period = h < 12 ? "AM" : "PM";
  const displayH = h % 12 === 0 ? 12 : h % 12;
  const mStr = m < 10 ? `0${m}` : `${m}`;
  return `${displayH}:${mStr} ${period}`;
}

// ─── Events — FIXED positions, fire at VO words ──────────────────────────────
const EVENTS = [
  { label: "COYOTE",   timeTag: "3:00 AM",   fireFrame: 285, x: 0.74, y: 0.35 },
  { label: "SICK COW", timeTag: "NOON",       fireFrame: 345, x: 0.28, y: 0.64 },
  { label: "EMPTY TANK",timeTag: "MIDNIGHT",  fireFrame: 405, x: 0.70, y: 0.72 },
] as const;

// Frame at which "all missed" callout appears
const ALL_MISSED_FRAME = 450;

export const TraditionalWay: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  // Fast fade-in — start at 30% opacity, reach 100% by f8 (prevents dim stall)
  const fadeIn = interpolate(frame, [0, 8], [0.30, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Truck position along road loop
  const lapT = (frame % LAP_FRAMES) / LAP_FRAMES;
  const truck = lerpWp(ROAD_WP, lapT);
  const tAngle = truckAngle(ROAD_WP, lapT);
  const clock = clockText(frame);

  // "All missed" banner
  const allMissedOp = interpolate(frame, [ALL_MISSED_FRAME, ALL_MISSED_FRAME + 18], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  // Sub-label appears at f260
  const subLabelOp = interpolate(frame, [260, 285], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: CREAM, opacity: fadeIn }}>
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

      {/* ── Ranch map SVG ── */}
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
        {/* Paddock 1 label */}
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
      </svg>

      {/* ── Truck emoji ── */}
      <div
        style={{
          position: "absolute",
          left: truck.x * width - 20,
          top: truck.y * height - 18,
          fontSize: 30,
          transform: `rotate(${tAngle}deg)`,
          filter: "drop-shadow(0 2px 6px rgba(0,0,0,0.28))",
          lineHeight: 1,
          zIndex: 10,
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
        // Full-map vignette at pulse: rendered via outer component
        const iconOp = hasStarted ? 1 : 0.18;
        const labelColor = hasStarted ? TERRACOTTA : SAGE_DARK;

        // Spring pop-in on first appearance
        const popSp = spring({
          frame: ev.fireFrame > 0 ? frame - ev.fireFrame : frame,
          fps,
          config: { damping: 80, stiffness: 280 },
        });
        const popScale = hasStarted ? interpolate(popSp, [0, 1], [0, 1], {
          extrapolateLeft: "clamp", extrapolateRight: "clamp",
        }) : 1;

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
            }}
          >
            {/* Expanding pulse ring */}
            <div style={{
              position: "absolute",
              width: 72,
              height: 72,
              borderRadius: "50%",
              border: `3px solid ${TERRACOTTA}`,
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
              border: `2px solid ${TERRACOTTA}`,
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
              filter: isRinging ? `drop-shadow(0 0 10px ${TERRACOTTA})` : "none",
              lineHeight: 1,
            }}>
              {ev.label === "COYOTE" ? "🐺" : ev.label === "SICK COW" ? "🐄" : "💧"}
            </div>

            {/* Label */}
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
              {hasStarted ? "MISSED" : ev.label}
            </div>

            {/* Time tag (shown after fire) */}
            {hasStarted && (
              <div style={{
                fontFamily: MONO,
                fontSize: 10,
                color: TERRACOTTA,
                opacity: 0.75,
                letterSpacing: "0.08em",
              }}>
                {ev.timeTag}
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
            opacity: vOp,
            pointerEvents: "none",
            zIndex: 15,
          }} />
        );
      })}

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
          opacity: subLabelOp,
          zIndex: 30,
        }}
      >
        1 rancher · 200 miles / week · events missed between runs
      </div>

      {/* ── "All Missed" + cost callout ── */}
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
          opacity: allMissedOp,
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
    </AbsoluteFill>
  );
};
