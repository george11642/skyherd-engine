/**
 * v2 shared atoms — lower-thirds, anchor chips, accent palette, kinetic punch.
 *
 * Used by both the AB 3-act layout and C's 5-act layout. Stripped of
 * Wes cowboy-isms and v1-specific copy. All v2 act components import from
 * here, not from acts/Act{1,2,3}*.tsx (those remain the v1 fallback path).
 */
import {
  AbsoluteFill,
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export type Accent = "sage" | "dust" | "sky" | "thermal" | "warn";

export const ACCENT_MAP: Record<Accent, string> = {
  sage: "rgb(148 176 136)",
  dust: "rgb(210 178 138)",
  sky: "rgb(120 180 220)",
  thermal: "rgb(255 143 60)",
  warn: "rgb(240 195 80)",
};

// ─── Lower-third (slide-in card with agent + detail) ─────────────────────────

export type LowerThirdProps = {
  agent: string;
  detail: string;
  accent: Accent;
  appearFrame: number;
  durationInFrames: number;
};

export const LowerThird = ({
  agent,
  detail,
  accent,
  appearFrame,
  durationInFrames,
}: LowerThirdProps) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const appearProgress = spring({
    frame: frame - appearFrame,
    fps,
    config: { damping: 120, stiffness: 180, mass: 0.7 },
  });
  const x = interpolate(appearProgress, [0, 1], [-60, 0]);
  const opacity = interpolate(appearProgress, [0, 1], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const exitOpacity = interpolate(
    frame,
    [appearFrame + durationInFrames - 20, appearFrame + durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  return (
    <div
      style={{
        position: "absolute",
        bottom: 90,
        left: 90,
        display: "flex",
        alignItems: "stretch",
        gap: 18,
        transform: `translateX(${x}px)`,
        opacity: Math.min(opacity, exitOpacity),
        backgroundColor: "rgba(16,19,25,0.78)",
        borderRadius: 8,
        backdropFilter: "blur(12px)",
        padding: "18px 26px",
        boxShadow: "0 10px 40px rgba(0,0,0,0.45)",
      }}
    >
      <div
        style={{
          width: 4,
          backgroundColor: ACCENT_MAP[accent],
          borderRadius: 2,
        }}
      />
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <div
          style={{
            fontFamily: "Inter, sans-serif",
            fontWeight: 700,
            fontSize: 24,
            color: "rgb(236 239 244)",
            letterSpacing: "-0.005em",
          }}
        >
          {agent}
        </div>
        <div
          style={{
            fontFamily: "Inter, sans-serif",
            fontWeight: 500,
            fontSize: 18,
            color: "rgb(168 180 198)",
            letterSpacing: "0.02em",
          }}
        >
          {detail}
        </div>
      </div>
    </div>
  );
};

// ─── Attestation anchor chip (top-right HashChip) ────────────────────────────

export type AnchorChipProps = {
  label: string;
  topic: string;
  hash: string;
  statusPill: string;
  appearFrame: number;
  accent: Accent;
};

export const AnchorChip = ({
  label,
  topic,
  hash,
  statusPill,
  appearFrame,
  accent,
}: AnchorChipProps) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({
    frame: frame - appearFrame,
    fps,
    config: { damping: 100, stiffness: 200 },
  });
  const scale = interpolate(p, [0, 1], [0.92, 1]);
  const opacity = interpolate(p, [0, 1], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const accentColor = ACCENT_MAP[accent];

  return (
    <div
      style={{
        position: "absolute",
        top: 90,
        right: 90,
        transform: `scale(${scale})`,
        opacity,
        fontFamily: "Inter, sans-serif",
        backgroundColor: "rgba(16,19,25,0.9)",
        border: `1px solid ${accentColor}`,
        borderRadius: 10,
        padding: "14px 18px",
        backdropFilter: "blur(12px)",
        boxShadow: "0 8px 32px rgba(0,0,0,0.55)",
        minWidth: 280,
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 14,
        }}
      >
        <div
          style={{
            fontSize: 11,
            color: accentColor,
            letterSpacing: "0.3em",
            textTransform: "uppercase",
            fontWeight: 700,
          }}
        >
          {label}
        </div>
        <div
          style={{
            fontSize: 10,
            color: "rgb(10 12 16)",
            backgroundColor: accentColor,
            padding: "3px 9px",
            borderRadius: 999,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            fontWeight: 800,
          }}
        >
          {statusPill}
        </div>
      </div>
      <div
        style={{
          fontSize: 20,
          color: "rgb(236 239 244)",
          fontWeight: 600,
          letterSpacing: "-0.005em",
        }}
      >
        {topic}
      </div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          borderTop: `1px solid rgba(148,176,136,0.18)`,
          paddingTop: 8,
        }}
      >
        <div
          style={{
            fontSize: 10,
            color: "rgb(120 132 148)",
            letterSpacing: "0.2em",
            textTransform: "uppercase",
            fontWeight: 600,
          }}
        >
          Ed25519
        </div>
        <div
          style={{
            fontFamily: "ui-monospace, JetBrains Mono, monospace",
            fontSize: 17,
            color: "rgb(236 239 244)",
            fontWeight: 500,
            letterSpacing: "0.02em",
          }}
        >
          {hash}
        </div>
      </div>
    </div>
  );
};

// ─── Kinetic punch words (one-by-one stagger) ────────────────────────────────

export type KineticPunchProps = {
  words: Array<{
    text: string;
    appearFrame: number;
    weight?: 400 | 500 | 600 | 700 | 800;
    size?: number;
    color?: string;
  }>;
  layout?: "stack" | "wrap";
};

export const KineticPunch = ({
  words,
  layout = "stack",
}: KineticPunchProps) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill
      style={{
        alignItems: "center",
        justifyContent: "center",
        padding: "0 12%",
        flexDirection: layout === "stack" ? "column" : "row",
        flexWrap: layout === "wrap" ? "wrap" : "nowrap",
        gap: layout === "stack" ? 28 : "0.5em",
      }}
    >
      {words.map((w, i) => {
        const p = spring({
          frame: frame - w.appearFrame,
          fps,
          config: { damping: 100, stiffness: 200, mass: 0.65 },
        });
        const y = interpolate(p, [0, 1], [40, 0]);
        const o = interpolate(p, [0, 1], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        return (
          <div
            key={`punch-${i}`}
            style={{
              transform: `translateY(${y}px)`,
              opacity: o,
              fontFamily: "Inter, sans-serif",
              fontWeight: w.weight ?? 700,
              fontSize: w.size ?? 72,
              color: w.color ?? "rgb(236 239 244)",
              letterSpacing: "-0.025em",
              lineHeight: 1.05,
              textAlign: "center",
              textShadow: "0 4px 28px rgba(0,0,0,0.55)",
            }}
          >
            {w.text}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// ─── Smooth fade utility ──────────────────────────────────────────────────────

export const useFadeInOut = (
  totalFrames: number,
  inFrames = 25,
  outFrames = 25,
): number => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, inFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.45, 0, 0.55, 1),
  });
  const fadeOut = interpolate(
    frame,
    [totalFrames - outFrames, totalFrames],
    [1, 0],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.45, 0, 0.55, 1),
    },
  );
  return Math.min(fadeIn, fadeOut);
};
