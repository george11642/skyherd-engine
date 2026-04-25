/**
 * TraditionalWay — Scene 0:18–0:35 (17s / 510 frames @ 30fps)
 *
 * Top-down ranch map with a truck driving a closed loop.
 * Time-of-day clock ticks in the corner.
 * At 3am / noon / midnight three event icons flash red — truck is NOT near them.
 */
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

// Cream-and-sage palette from acts/v2/shared.tsx
const CREAM = "rgb(245 240 230)";
const CREAM_DARK = "rgb(228 220 205)";
const SAGE = "rgb(148 176 136)";
const SAGE_DARK = "rgb(100 130 90)";
const TERRACOTTA = "rgb(188 90 60)";
const INK = "rgb(45 42 38)";
const MONO = "ui-monospace, 'JetBrains Mono', monospace";
const SERIF = "Georgia, 'Times New Roman', serif";

// Truck moves along a rectangular path. Returns {x,y} fraction of canvas.
function truckPos(frame: number, fps: number): { x: number; y: number } {
  const period = fps * 10; // full lap = 10 seconds
  const t = ((frame % period) / period) * 4; // 0..4 = 4 segments
  if (t < 1) return { x: 0.2 + t * 0.6, y: 0.25 };          // top
  if (t < 2) return { x: 0.8, y: 0.25 + (t - 1) * 0.5 };    // right
  if (t < 3) return { x: 0.8 - (t - 2) * 0.6, y: 0.75 };    // bottom
  return { x: 0.2, y: 0.75 - (t - 3) * 0.5 };                // left
}

function truckAngle(frame: number, fps: number): number {
  const period = fps * 10;
  const t = ((frame % period) / period) * 4;
  if (t < 1) return 0;
  if (t < 2) return 90;
  if (t < 3) return 180;
  return 270;
}

// Clock ticks: advances minute per 6 frames. Start at 00:00.
function clockText(frame: number, fps: number): string {
  const totalMinutes = Math.floor((frame / fps) * 60); // 60 min per second of video → fast clock
  const minutesInDay = totalMinutes % (24 * 60);
  const h = Math.floor(minutesInDay / 60) % 24;
  const m = minutesInDay % 60;
  const period = h < 12 ? "AM" : "PM";
  const displayH = h % 12 === 0 ? 12 : h % 12;
  const mStr = m < 10 ? `0${m}` : `${m}`;
  return `${displayH}:${mStr} ${period}`;
}

// Events flash red at specific clock angles (3am=90min, noon=720min, midnight=0min)
// We approximate: event pulses at frames 60, 240, 420 (roughly 3 bursts in 17s)
const EVENT_FRAMES = [60, 230, 420];
const EVENTS = [
  { label: "COYOTE", icon: "🐺", x: 0.68, y: 0.32 },
  { label: "SICK COW", icon: "🐄", x: 0.28, y: 0.65 },
  { label: "TANK", icon: "💧", x: 0.72, y: 0.7 },
];

export const TraditionalWay: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const fadeIn = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const truck = truckPos(frame, fps);
  const angle = truckAngle(frame, fps);
  const clock = clockText(frame, fps);

  return (
    <AbsoluteFill style={{ backgroundColor: CREAM, opacity: fadeIn }}>
      {/* Title */}
      <div
        style={{
          position: "absolute",
          top: 48,
          left: 0,
          right: 0,
          textAlign: "center",
          fontFamily: SERIF,
          fontWeight: 700,
          fontSize: 38,
          color: INK,
          letterSpacing: "-0.01em",
        }}
      >
        How a Ranch Runs Today
      </div>

      {/* Ranch map background */}
      <svg
        style={{ position: "absolute", inset: 0 }}
        viewBox={`0 0 ${width} ${height}`}
        width={width}
        height={height}
      >
        {/* Ranch boundary */}
        <rect
          x={width * 0.12}
          y={height * 0.16}
          width={width * 0.76}
          height={height * 0.68}
          rx={18}
          fill={CREAM_DARK}
          stroke={SAGE}
          strokeWidth={3}
        />
        {/* Fence line — top edge */}
        {[...Array(14)].map((_, i) => (
          <line
            key={`fence-t-${i}`}
            x1={width * 0.12 + i * (width * 0.76 / 13)}
            y1={height * 0.16}
            x2={width * 0.12 + i * (width * 0.76 / 13)}
            y2={height * 0.16 + 14}
            stroke={SAGE_DARK}
            strokeWidth={2}
          />
        ))}
        {/* Truck route dashed loop */}
        <rect
          x={width * 0.18}
          y={height * 0.24}
          width={width * 0.64}
          height={height * 0.52}
          rx={10}
          fill="none"
          stroke={SAGE}
          strokeWidth={3}
          strokeDasharray="16 10"
        />
        {/* Pasture patches */}
        <ellipse cx={width * 0.32} cy={height * 0.45} rx={60} ry={40} fill="rgb(168 196 155 / 0.4)" />
        <ellipse cx={width * 0.65} cy={height * 0.55} rx={50} ry={35} fill="rgb(168 196 155 / 0.4)" />
        {/* Water trough marker */}
        <rect x={width * 0.7} y={height * 0.67} width={20} height={12} rx={3} fill="rgb(120 180 220 / 0.7)" />
      </svg>

      {/* Truck */}
      <div
        style={{
          position: "absolute",
          left: truck.x * width - 22,
          top: truck.y * height - 16,
          fontSize: 32,
          transform: `rotate(${angle}deg)`,
          filter: "drop-shadow(0 2px 6px rgba(0,0,0,0.25))",
          transition: "none",
          lineHeight: 1,
        }}
      >
        🚗
      </div>

      {/* Event icons that flash red */}
      {EVENTS.map((ev, i) => {
        const nearestPulse = EVENT_FRAMES[i] ?? 60;
        const pulseAge = frame - nearestPulse;
        const isActive = pulseAge >= 0 && pulseAge < 45;
        const pulseScale = isActive
          ? interpolate(pulseAge, [0, 10, 25, 45], [0.8, 1.3, 1.1, 1.0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            })
          : 1;
        const ringOpacity = isActive
          ? interpolate(pulseAge, [0, 20, 45], [0, 0.9, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            })
          : 0;

        return (
          <div
            key={ev.label}
            style={{
              position: "absolute",
              left: ev.x * width - 32,
              top: ev.y * height - 32,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 4,
            }}
          >
            {/* Pulse ring */}
            <div
              style={{
                position: "absolute",
                width: 64,
                height: 64,
                borderRadius: "50%",
                border: `3px solid ${TERRACOTTA}`,
                opacity: ringOpacity,
                transform: `scale(${pulseScale * 1.2})`,
                top: -4,
                left: -4,
              }}
            />
            {/* Icon */}
            <div
              style={{
                fontSize: 28,
                transform: `scale(${isActive ? pulseScale : 1})`,
                filter: isActive ? `drop-shadow(0 0 8px ${TERRACOTTA})` : "none",
                lineHeight: 1,
              }}
            >
              {ev.icon}
            </div>
            {/* Label */}
            <div
              style={{
                fontFamily: MONO,
                fontSize: 10,
                color: isActive ? TERRACOTTA : SAGE_DARK,
                fontWeight: 700,
                letterSpacing: "0.12em",
                textTransform: "uppercase",
                whiteSpace: "nowrap",
              }}
            >
              {isActive ? "MISSED" : ev.label}
            </div>
          </div>
        );
      })}

      {/* Clock */}
      <div
        style={{
          position: "absolute",
          bottom: 60,
          right: 80,
          backgroundColor: "rgba(45,42,38,0.88)",
          borderRadius: 10,
          padding: "12px 22px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 4,
        }}
      >
        <div
          style={{
            fontFamily: MONO,
            fontSize: 11,
            color: SAGE,
            letterSpacing: "0.22em",
            textTransform: "uppercase",
          }}
        >
          Ranch Time
        </div>
        <div
          style={{
            fontFamily: MONO,
            fontSize: 30,
            color: CREAM,
            fontWeight: 700,
            letterSpacing: "0.04em",
          }}
        >
          {clock}
        </div>
      </div>

      {/* Sub-label */}
      <div
        style={{
          position: "absolute",
          bottom: 60,
          left: 0,
          right: 0,
          textAlign: "center",
          fontFamily: MONO,
          fontSize: 16,
          color: TERRACOTTA,
          letterSpacing: "0.14em",
          textTransform: "uppercase",
          opacity: interpolate(frame, [240, 270], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        200 miles / week · events missed between runs
      </div>
    </AbsoluteFill>
  );
};
