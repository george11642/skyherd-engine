/**
 * v2 — Variants A & B Act 3 (Close, 30s).
 *
 * Substance VO + signals (18s) → wordmark + final VO (12s).
 */
import {
  AbsoluteFill,
  Audio,
  Series,
  Video,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { AB_LAYOUT } from "../../compositions/calculate-main-metadata";
import { ACCENT_MAP, useFadeInOut } from "./shared";

const FPS = 30;

// ── Substance beat (18s) ─────────────────────────────────────────────────────
const SubstanceBeat = () => {
  const frame = useCurrentFrame();
  const { durationInFrames, fps } = useVideoConfig();
  const opacity = useFadeInOut(durationInFrames, 30, 25);

  const blocks = [
    { at: 30, text: "1,106 tests · 87% coverage" },
    { at: 150, text: "Ed25519 attestation chain · 360 events" },
    { at: 270, text: "Fresh-clone reproducible · < 3 minutes" },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(8 10 14)", opacity }}>
      <Audio src={staticFile("voiceover/vo-close-substance.mp3")} />
      {/* Drone-rangeland B-roll placeholder — falls back to ambient_30x */}
      <Video
        src={staticFile("clips/ambient_30x_synthesis.mp4")}
        startFrom={0}
        endAt={durationInFrames + 60}
        muted
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          filter: "saturate(0.85) brightness(0.75)",
        }}
      />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(90deg, rgba(6,8,12,0.85) 0%, rgba(6,8,12,0.45) 60%, rgba(6,8,12,0.45) 100%)",
        }}
      />

      <div
        style={{
          position: "absolute",
          left: 100,
          top: "30%",
          maxWidth: 900,
          fontFamily: "Inter, sans-serif",
        }}
      >
        <div
          style={{
            fontSize: 14,
            color: ACCENT_MAP.sage,
            letterSpacing: "0.34em",
            textTransform: "uppercase",
            fontWeight: 600,
            marginBottom: 28,
          }}
        >
          Substance · provable
        </div>
        {blocks.map((b, i) => {
          const p = spring({
            frame: frame - b.at,
            fps,
            config: { damping: 100, stiffness: 200, mass: 0.7 },
          });
          const x = interpolate(p, [0, 1], [40, 0]);
          const o = interpolate(p, [0, 1], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return (
            <div
              key={`block-${i}`}
              style={{
                transform: `translateX(${x}px)`,
                opacity: o,
                fontSize: 44,
                fontWeight: 700,
                color: i === 1 ? ACCENT_MAP.dust : "rgb(236 239 244)",
                letterSpacing: "-0.018em",
                marginBottom: 18,
                lineHeight: 1.15,
                textShadow: "0 6px 24px rgba(0,0,0,0.6)",
              }}
            >
              {b.text}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ── Final wordmark beat (12s) ────────────────────────────────────────────────
const FinalBeat = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const fadeIn = interpolate(frame, [0, 25], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 25, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const opacity = Math.min(fadeIn, fadeOut);

  const wordmarkP = spring({
    frame: frame - 10,
    fps,
    config: { damping: 120, stiffness: 150, mass: 0.8 },
  });
  const wordmarkScale = interpolate(wordmarkP, [0, 1], [0.9, 1]);
  const wordmarkOpacity = interpolate(wordmarkP, [0, 1], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const linesOpacity = interpolate(frame, [60, 110], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "rgb(248 244 234)",
        alignItems: "center",
        justifyContent: "center",
        opacity,
      }}
    >
      <Audio src={staticFile("voiceover/vo-close-final.mp3")} />

      {/* Isometric brand placeholder — radial sage glow over warm cream */}
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse 70% 55% at 50% 50%, rgba(210,178,138,0.45) 0%, rgba(248,244,234,0) 80%)",
        }}
      />

      <div
        style={{
          transform: `scale(${wordmarkScale})`,
          opacity: wordmarkOpacity,
          fontFamily: "Inter, sans-serif",
          fontWeight: 800,
          fontSize: 200,
          color: "rgb(40 56 44)",
          letterSpacing: "-0.04em",
          lineHeight: 1,
          zIndex: 1,
        }}
      >
        Sky<span style={{ color: ACCENT_MAP.sage }}>Herd</span>
      </div>

      <div
        style={{
          marginTop: 50,
          opacity: linesOpacity,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 14,
          fontFamily: "Inter, sans-serif",
          color: "rgb(72 84 76)",
          textAlign: "center",
          zIndex: 1,
        }}
      >
        <div
          style={{
            fontSize: 28,
            color: "rgb(132 92 56)",
            fontWeight: 600,
            letterSpacing: "0.02em",
          }}
        >
          github.com/george11642/skyherd-engine
        </div>
        <div
          style={{
            fontSize: 18,
            fontFamily:
              "ui-monospace, JetBrains Mono, Cascadia Code, monospace",
            color: "rgb(72 84 76)",
            letterSpacing: "0.02em",
          }}
        >
          MIT · Python 3.11 · TypeScript 5.8 · Opus 4.7 · 1106 tests · 87% coverage · Ed25519
        </div>
        <div
          style={{
            fontSize: 16,
            color: "rgb(120 132 124)",
            letterSpacing: "0.24em",
            textTransform: "uppercase",
            fontWeight: 600,
            marginTop: 10,
          }}
        >
          George Teifel · UNM · 2026
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── Act 3 root ───────────────────────────────────────────────────────────────
export const ABAct3Close = () => {
  const SUBSTANCE = AB_LAYOUT.act3.substanceSeconds * FPS; // 540
  const FINAL = AB_LAYOUT.act3.finalSeconds * FPS; // 360

  return (
    <AbsoluteFill>
      <Series>
        <Series.Sequence durationInFrames={SUBSTANCE}>
          <SubstanceBeat />
        </Series.Sequence>
        <Series.Sequence durationInFrames={FINAL}>
          <FinalBeat />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};
