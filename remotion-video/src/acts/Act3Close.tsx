import {
  AbsoluteFill,
  Audio,
  Easing,
  Series,
  Video,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import type { VoDurationsFrames } from "../compositions/calculate-main-metadata";

type Act3Props = {
  voDurationsFrames: VoDurationsFrames;
};

const FPS = 30;

// ── Beat 1: Split-screen attestation (20 s) ──────────────────────────────────
const BeatAttest = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const fadeIn = interpolate(frame, [0, 20], [0, 1], {
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

  const lowerP = spring({
    frame: frame - 45,
    fps: 30,
    config: { damping: 120, stiffness: 180 },
  });
  const lowerY = interpolate(lowerP, [0, 1], [30, 0]);

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(6 8 12)" }}>
      <Audio src={staticFile("voiceover/wes-attest.mp3")} />

      {/* Left column */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "50%",
          height: "100%",
          overflow: "hidden",
          opacity,
        }}
      >
        <Video
          src={staticFile("clips/attest_verify.mp4")}
          startFrom={0}
          endAt={600}
          muted
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
        <div
          style={{
            position: "absolute",
            top: 40,
            left: 40,
            fontFamily: "Inter, sans-serif",
            fontSize: 14,
            color: "rgb(148 176 136)",
            letterSpacing: "0.32em",
            textTransform: "uppercase",
            fontWeight: 600,
            backgroundColor: "rgba(10,12,16,0.65)",
            padding: "6px 14px",
            borderRadius: 4,
            border: "1px solid rgba(148,176,136,0.35)",
          }}
        >
          skyherd-verify
        </div>
      </div>

      {/* Right column */}
      <div
        style={{
          position: "absolute",
          top: 0,
          right: 0,
          width: "50%",
          height: "100%",
          overflow: "hidden",
          opacity,
        }}
      >
        <Video
          src={staticFile("clips/fresh_clone.mp4")}
          startFrom={0}
          endAt={600}
          muted
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
        <div
          style={{
            position: "absolute",
            top: 40,
            right: 40,
            fontFamily: "Inter, sans-serif",
            fontSize: 14,
            color: "rgb(210 178 138)",
            letterSpacing: "0.32em",
            textTransform: "uppercase",
            fontWeight: 600,
            backgroundColor: "rgba(10,12,16,0.65)",
            padding: "6px 14px",
            borderRadius: 4,
            border: "1px solid rgba(210,178,138,0.35)",
          }}
        >
          fresh clone · &lt; 3 min
        </div>
      </div>

      {/* Thin sage divider */}
      <div
        style={{
          position: "absolute",
          top: "8%",
          bottom: "8%",
          left: "50%",
          width: 2,
          backgroundColor: "rgba(148,176,136,0.55)",
          boxShadow: "0 0 22px rgba(148,176,136,0.4)",
          transform: "translateX(-1px)",
          opacity,
        }}
      />

      {/* Lower-third */}
      <div
        style={{
          position: "absolute",
          bottom: 70,
          left: "50%",
          transform: `translate(-50%, ${lowerY}px)`,
          opacity: lowerP * opacity,
          fontFamily: "Inter, sans-serif",
          textAlign: "center",
          backgroundColor: "rgba(10,12,16,0.82)",
          backdropFilter: "blur(12px)",
          padding: "18px 34px",
          borderRadius: 10,
          border: "1px solid rgba(148,176,136,0.25)",
          boxShadow: "0 12px 40px rgba(0,0,0,0.55)",
        }}
      >
        <div
          style={{
            fontSize: 14,
            color: "rgb(148 176 136)",
            letterSpacing: "0.34em",
            textTransform: "uppercase",
            fontWeight: 600,
            marginBottom: 8,
          }}
        >
          Act III · Provable
        </div>
        <div
          style={{
            fontSize: 30,
            fontWeight: 700,
            color: "rgb(236 239 244)",
            letterSpacing: "-0.01em",
          }}
        >
          Ed25519 Merkle chain · 360 signed events · Repro &lt; 3 min
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── Beat 2: Kinetic "Why it matters" (15 s) ──────────────────────────────────
const WHY_LINES = [
  "Beef: record highs.",
  "Herd: 65-year low.",
  "Ranchers can't hire their way out.",
  "The ranch has to watch itself.",
];

const BeatWhy = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Placeholder Ken-Burns "ranch photo" — sage/dust gradient. Slow zoom.
  const scale = interpolate(
    frame,
    [0, durationInFrames],
    [1.0, 1.22],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const panX = interpolate(frame, [0, durationInFrames], [0, -80]);

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

  // Each line appears with a stagger.
  const LINE_STAGGER = 75; // 2.5 s
  const LINE_START = 30;

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(6 8 12)" }}>
      <Audio src={staticFile("voiceover/wes-why.mp3")} />

      {/* Ken-Burns gradient backdrop */}
      <div
        style={{
          position: "absolute",
          inset: -80,
          transform: `scale(${scale}) translateX(${panX}px)`,
          background:
            "radial-gradient(circle at 30% 45%, rgba(210,178,138,0.28) 0%, rgba(148,176,136,0.12) 35%, rgba(10,12,16,1) 75%)",
          opacity,
        }}
      />
      {/* Grain-like noise via second gradient */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(6,8,12,0.2) 0%, rgba(6,8,12,0.65) 100%)",
          opacity,
        }}
      />
      {/* Horizon line */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: "62%",
          height: 1,
          backgroundColor: "rgba(210,178,138,0.22)",
          opacity,
        }}
      />

      {/* Stacked lines */}
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          padding: "0 10%",
          flexDirection: "column",
          gap: 24,
        }}
      >
        {WHY_LINES.map((line, i) => {
          const appearAt = LINE_START + i * LINE_STAGGER;
          const p = spring({
            frame: frame - appearAt,
            fps,
            config: { damping: 100, stiffness: 200, mass: 0.7 },
          });
          const y = interpolate(p, [0, 1], [60, 0]);
          const o = interpolate(p, [0, 1], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          const isClosing = i === WHY_LINES.length - 1;
          return (
            <div
              key={`line-${i}`}
              style={{
                transform: `translateY(${y}px)`,
                opacity: o * opacity,
                fontFamily: "Inter, sans-serif",
                fontWeight: isClosing ? 800 : 600,
                fontSize: isClosing ? 82 : 58,
                color: isClosing ? "rgb(210 178 138)" : "rgb(236 239 244)",
                letterSpacing: "-0.02em",
                textAlign: "center",
                lineHeight: 1.1,
                textShadow: "0 6px 28px rgba(0,0,0,0.6)",
              }}
            >
              {line}
            </div>
          );
        })}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ── Beat 3: Final close (5 s) ────────────────────────────────────────────────
const BeatFinal = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

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

  const linesOpacity = interpolate(
    frame,
    [40, 70],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const finalFadeOut = interpolate(
    frame,
    [durationInFrames - 20, durationInFrames],
    [1, 0],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.45, 0, 0.55, 1),
    },
  );

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "rgb(6 8 12)",
        alignItems: "center",
        justifyContent: "center",
        opacity: finalFadeOut,
      }}
    >
      <Audio src={staticFile("voiceover/wes-close.mp3")} />

      {/* Wordmark */}
      <div
        style={{
          transform: `scale(${wordmarkScale})`,
          opacity: wordmarkOpacity,
          fontFamily: "Inter, sans-serif",
          fontWeight: 800,
          fontSize: 180,
          color: "rgb(236 239 244)",
          letterSpacing: "-0.04em",
          lineHeight: 1,
          textShadow: "0 12px 60px rgba(148,176,136,0.25)",
        }}
      >
        Sky<span style={{ color: "rgb(148 176 136)" }}>Herd</span>
      </div>

      {/* Lines below */}
      <div
        style={{
          marginTop: 50,
          opacity: linesOpacity,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 14,
          fontFamily: "Inter, sans-serif",
          color: "rgb(168 180 198)",
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontSize: 28,
            color: "rgb(210 178 138)",
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
            color: "rgb(168 180 198)",
            letterSpacing: "0.02em",
          }}
        >
          MIT · Python 3.11 · TypeScript 5.8 · Opus 4.7 · 1106 tests · 87%
          coverage
        </div>
        <div
          style={{
            fontSize: 16,
            color: "rgb(110 122 140)",
            letterSpacing: "0.24em",
            textTransform: "uppercase",
            fontWeight: 600,
            marginTop: 10,
          }}
        >
          George Teifel · UNM · 2026-04-26
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const Act3Close = ({ voDurationsFrames }: Act3Props) => {
  const ATTEST = 20 * FPS; // 600
  const WHY = 15 * FPS; // 450
  const CLOSE = 5 * FPS; // 150

  // Silence unused-prop TS warning; metadata reads this in case a swap is
  // needed later.
  void voDurationsFrames;

  return (
    <AbsoluteFill>
      <Series>
        <Series.Sequence durationInFrames={ATTEST}>
          <BeatAttest />
        </Series.Sequence>
        <Series.Sequence durationInFrames={WHY}>
          <BeatWhy />
        </Series.Sequence>
        <Series.Sequence durationInFrames={CLOSE}>
          <BeatFinal />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};
