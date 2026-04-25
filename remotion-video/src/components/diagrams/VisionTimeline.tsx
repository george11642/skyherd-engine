/**
 * VisionTimeline — Scene 2:10–2:32 (22s / 660 frames @ 30fps)
 *
 * Horizontal timeline L→R with 4 milestones.
 * Line draws left-to-right, each milestone dot + label reveals as line passes it.
 * "TODAY" pulses at end to anchor the present.
 */
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

const CREAM = "rgb(245 240 230)";
const CREAM_DARK = "rgb(228 220 205)";
const SAGE = "rgb(148 176 136)";
const TERRACOTTA = "rgb(188 90 60)";
const INK = "rgb(45 42 38)";
const INK_LIGHT = "rgb(110 105 96)";
const MONO = "ui-monospace, 'JetBrains Mono', monospace";
const SERIF = "Georgia, 'Times New Roman', serif";

interface Milestone {
  label: string;
  sub: string;
  isNow: boolean;
  xFrac: number; // fraction of timeline width (0..1)
}

const MILESTONES: Milestone[] = [
  {
    label: "TODAY",
    sub: "Software MVP + Simulator",
    isNow: true,
    xFrac: 0.07,
  },
  {
    label: "6 MONTHS",
    sub: "Pilot ranches · New Mexico",
    isNow: false,
    xFrac: 0.35,
  },
  {
    label: "1 YEAR",
    sub: "10 ranches · Pi cameras · LoRa",
    isNow: false,
    xFrac: 0.64,
  },
  {
    label: "5 YEARS",
    sub: "Every ranch in America",
    isNow: false,
    xFrac: 0.93,
  },
];

// Timeline line draws over frames 30..210 (6s at 30fps)
const LINE_START = 30;
const LINE_END = 210;

export const VisionTimeline: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const fadeIn = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // How far the line has drawn (0..1)
  const lineProgress = interpolate(frame, [LINE_START, LINE_END], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const timelineY = height * 0.52;
  const timelineLeft = width * 0.06;
  const timelineRight = width * 0.94;
  const timelineW = timelineRight - timelineLeft;
  const dotRadius = 16;

  // "TODAY" pulses after everything builds
  const todayPulse = frame > LINE_END + 30
    ? Math.sin(((frame - LINE_END - 30) / fps) * Math.PI * 1.5) * 0.3 + 0.7
    : 1;

  return (
    <AbsoluteFill style={{ backgroundColor: CREAM, opacity: fadeIn }}>
      {/* Title */}
      <div
        style={{
          position: "absolute",
          top: 56,
          left: 0,
          right: 0,
          textAlign: "center",
          fontFamily: SERIF,
          fontWeight: 700,
          fontSize: 36,
          color: INK,
          letterSpacing: "-0.01em",
        }}
      >
        The Road Ahead
      </div>

      {/* SVG — timeline line + dots */}
      <svg
        style={{ position: "absolute", inset: 0, overflow: "visible" }}
        viewBox={`0 0 ${width} ${height}`}
        width={width}
        height={height}
      >
        {/* Background track */}
        <line
          x1={timelineLeft}
          y1={timelineY}
          x2={timelineRight}
          y2={timelineY}
          stroke={CREAM_DARK}
          strokeWidth={6}
          strokeLinecap="round"
        />
        {/* Animated progress line */}
        <line
          x1={timelineLeft}
          y1={timelineY}
          x2={timelineLeft + timelineW * lineProgress}
          y2={timelineY}
          stroke={SAGE}
          strokeWidth={6}
          strokeLinecap="round"
        />
        {/* Dots */}
        {MILESTONES.map((m, i) => {
          const dotX = timelineLeft + m.xFrac * timelineW;
          const revealed = lineProgress >= m.xFrac;
          const dotOpacity = revealed ? 1 : 0;
          const dotScale = revealed
            ? 1 + (m.isNow ? (todayPulse - 1) * 0.4 : 0)
            : 0;
          const dotColor = m.isNow ? TERRACOTTA : SAGE;

          return (
            <g key={m.label} opacity={dotOpacity}>
              {/* Outer ring for NOW */}
              {m.isNow && (
                <circle
                  cx={dotX}
                  cy={timelineY}
                  r={dotRadius * 1.7 * dotScale}
                  fill="none"
                  stroke={TERRACOTTA}
                  strokeWidth={2}
                  opacity={0.4 * todayPulse}
                />
              )}
              {/* Main dot */}
              <circle
                cx={dotX}
                cy={timelineY}
                r={dotRadius * dotScale}
                fill={dotColor}
              />
              {/* Connector tick */}
              <line
                x1={dotX}
                y1={timelineY - dotRadius}
                x2={dotX}
                y2={timelineY - dotRadius - 24}
                stroke={dotColor}
                strokeWidth={2}
                strokeLinecap="round"
              />
            </g>
          );
        })}
      </svg>

      {/* Labels — rendered as DOM for better text control */}
      {MILESTONES.map((m, i) => {
        const dotX = timelineLeft + m.xFrac * timelineW;
        const revealed = lineProgress >= m.xFrac;
        const labelOpacity = revealed
          ? interpolate(
              lineProgress,
              [m.xFrac, m.xFrac + 0.05],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
            )
          : 0;

        // Stack above or below alternately
        const isAbove = i % 2 === 0;
        const vertOffset = isAbove ? -140 : 60;

        return (
          <div
            key={`label-${m.label}`}
            style={{
              position: "absolute",
              left: dotX - 110,
              top: timelineY + vertOffset,
              width: 220,
              textAlign: "center",
              opacity: labelOpacity,
            }}
          >
            <div
              style={{
                fontFamily: MONO,
                fontWeight: 800,
                fontSize: m.isNow ? 20 : 16,
                color: m.isNow ? TERRACOTTA : INK,
                letterSpacing: "0.14em",
                textTransform: "uppercase",
                marginBottom: 6,
              }}
            >
              {m.label}
            </div>
            <div
              style={{
                fontFamily: SERIF,
                fontSize: 17,
                color: INK_LIGHT,
                lineHeight: 1.35,
              }}
            >
              {m.sub}
            </div>
          </div>
        );
      })}

      {/* Bottom callout */}
      <div
        style={{
          position: "absolute",
          bottom: 44,
          left: 0,
          right: 0,
          textAlign: "center",
          fontFamily: MONO,
          fontSize: 14,
          color: SAGE,
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          opacity: interpolate(frame, [LINE_END + 30, LINE_END + 60], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        Every ranch in America deserves a nervous system
      </div>
    </AbsoluteFill>
  );
};
