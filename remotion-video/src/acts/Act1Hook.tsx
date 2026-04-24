import {
  AbsoluteFill,
  Audio,
  Easing,
  Sequence,
  Video,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import type { VoDurationsFrames } from "../compositions/calculate-main-metadata";

type Act1Props = {
  voDurationsFrames: VoDurationsFrames;
};

const HOOK_LINE =
  "A cow can be dying for 72 hours before anyone sees it.";

const GEORGE_WORDS = [
  "George.",
  "Licensed",
  "drone",
  "op.",
  "Built",
  "SkyHerd",
  "with",
  "Opus",
  "4.7.",
];

// ── Beat 1: Black-card typewriter (frames 0–90, 3 s) ─────────────────────────
const Beat1Typewriter = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const charProgress = interpolate(frame, [10, 75], [0, HOOK_LINE.length], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.45, 0, 0.55, 1),
  });
  const visible = HOOK_LINE.slice(0, Math.floor(charProgress));
  const cursorOn = Math.floor(frame / (fps / 3)) % 2 === 0;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "rgb(6 8 12)",
        alignItems: "center",
        justifyContent: "center",
        padding: "0 12%",
      }}
    >
      <div
        style={{
          fontFamily: "Inter, sans-serif",
          fontWeight: 500,
          fontSize: 54,
          lineHeight: 1.25,
          color: "rgb(236 239 244)",
          textAlign: "center",
          letterSpacing: "-0.01em",
        }}
      >
        {visible}
        <span
          style={{
            display: "inline-block",
            width: "0.6ch",
            opacity: cursorOn ? 1 : 0,
            color: "rgb(148 176 136)",
          }}
        >
          |
        </span>
      </div>
    </AbsoluteFill>
  );
};

// ── Beat 2: Crossfade to ambient establish clip (frames 90–240, 5 s) ─────────
const Beat2Crossfade = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Local frame = 0..150; 0..30 is the crossfade in.
  const fadeIn = interpolate(frame, [0, 30], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(frame, [120, 150], [1, 0.3], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const opacity = Math.min(fadeIn, fadeOut);

  void fps;

  return (
    <AbsoluteFill>
      <Video
        src={staticFile("clips/ambient_establish.mp4")}
        startFrom={0}
        endAt={150}
        muted
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          opacity,
          filter: "saturate(0.85) contrast(1.05)",
        }}
      />
      {/* Warm sage tint overlay */}
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at center, rgba(148,176,136,0.08) 0%, rgba(10,12,16,0.55) 90%)",
          opacity,
        }}
      />
      {/* Subtle lower-third ident */}
      <div
        style={{
          position: "absolute",
          bottom: 80,
          left: 100,
          fontFamily: "Inter, sans-serif",
          color: "rgb(236 239 244)",
          fontSize: 22,
          letterSpacing: "0.28em",
          textTransform: "uppercase",
          opacity: opacity * 0.9,
        }}
      >
        <span style={{ color: "rgb(148 176 136)" }}>SkyHerd</span>
        <span style={{ opacity: 0.55, marginLeft: 20 }}>
          Ranch A · 40,000 acres
        </span>
      </div>
    </AbsoluteFill>
  );
};

// ── Beat 3: Kinetic-typography George replacement (frames 240–540, 10 s) ─────
const Beat3George = ({ voDurationsFrames }: Act1Props) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Background ambient clip dimmed to 20% opacity.
  const bgOpacity = interpolate(frame, [0, 20], [0, 0.2], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Reveal each word ~22 frames apart with a spring.
  const WORD_STAGGER = 22;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "rgb(6 8 12)",
      }}
    >
      {/* Background dimmed video */}
      <Video
        src={staticFile("clips/ambient_establish.mp4")}
        startFrom={150}
        endAt={450}
        muted
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          opacity: bgOpacity,
          filter: "blur(2px) saturate(0.8)",
        }}
      />

      {/* Dark gradient overlay */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(6,8,12,0.55) 0%, rgba(6,8,12,0.85) 100%)",
        }}
      />

      {/* Wes VO (george-hook) */}
      <Audio src={staticFile("voiceover/wes-george-hook.mp3")} />

      {/* Kinetic words */}
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          padding: "0 8%",
          flexDirection: "column",
          gap: 32,
        }}
      >
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            columnGap: "0.9em",
            rowGap: "0.25em",
            justifyContent: "center",
            maxWidth: 1400,
          }}
        >
          {GEORGE_WORDS.map((word, i) => {
            const start = i * WORD_STAGGER;
            const progress = spring({
              frame: frame - start,
              fps,
              config: { damping: 100, stiffness: 200, mass: 0.6 },
            });
            const translateY = interpolate(progress, [0, 1], [80, 0]);
            const opacity = interpolate(progress, [0, 1], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            const isAccent =
              word === "SkyHerd" ||
              word === "Opus" ||
              word === "4.7." ||
              word === "George.";
            return (
              <span
                key={`${word}-${i}`}
                style={{
                  display: "inline-block",
                  fontFamily: "Inter, sans-serif",
                  fontWeight: 700,
                  fontSize: 78,
                  lineHeight: 1.08,
                  color: isAccent
                    ? "rgb(210 178 138)"
                    : "rgb(236 239 244)",
                  transform: `translateY(${translateY}px)`,
                  opacity,
                  letterSpacing: "-0.025em",
                  textShadow: "0 4px 28px rgba(0,0,0,0.55)",
                  whiteSpace: "nowrap",
                }}
              >
                {word}
              </span>
            );
          })}
        </div>

        {/* Caption line below */}
        <div
          style={{
            fontFamily: "Inter, sans-serif",
            fontSize: 24,
            color: "rgb(168 180 198)",
            letterSpacing: "0.22em",
            textTransform: "uppercase",
            opacity: interpolate(
              frame,
              [GEORGE_WORDS.length * WORD_STAGGER, GEORGE_WORDS.length * WORD_STAGGER + 40],
              [0, 0.9],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
            ),
          }}
        >
          Built for Opus 4.7 · Hackathon Submission
        </div>
      </AbsoluteFill>

      {/* Sage edge card frame */}
      <AbsoluteFill
        style={{
          boxShadow: "inset 0 0 0 2px rgba(148,176,136,0.14)",
          pointerEvents: "none",
        }}
      />
      {/* Silence the prop-only reference so TS doesn't flag it */}
      <div style={{ display: "none" }}>{voDurationsFrames.georgeHook}</div>
    </AbsoluteFill>
  );
};

// ── Beat 4: Dashboard pitch + wordmark reveal (frames 540–720, 6 s) ──────────
const Beat4Pitch = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const fade = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Wordmark spring from right.
  const wordmarkProgress = spring({
    frame: frame - 30,
    fps,
    config: { damping: 100, stiffness: 180, mass: 0.8 },
  });
  const wordmarkX = interpolate(wordmarkProgress, [0, 1], [120, 0]);

  // Subtitle fade in.
  const subtitleOpacity = interpolate(frame, [60, 100], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(10 12 16)" }}>
      <Video
        src={staticFile("clips/ambient_establish.mp4")}
        startFrom={300}
        endAt={480}
        muted
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          opacity: fade,
        }}
      />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(10,12,16,0) 45%, rgba(10,12,16,0.78) 100%)",
        }}
      />

      {/* Subtitle top-center */}
      <div
        style={{
          position: "absolute",
          top: 80,
          width: "100%",
          textAlign: "center",
          fontFamily: "Inter, sans-serif",
          fontSize: 32,
          color: "rgb(236 239 244)",
          letterSpacing: "-0.005em",
          opacity: subtitleOpacity,
          padding: "0 8%",
        }}
      >
        SkyHerd. Five Claude Managed Agents watching a ranch 24/7.
      </div>

      {/* Wordmark bottom-right */}
      <div
        style={{
          position: "absolute",
          bottom: 90,
          right: 100,
          transform: `translateX(${wordmarkX}px)`,
          opacity: wordmarkProgress,
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-end",
          gap: 8,
        }}
      >
        <div
          style={{
            fontFamily: "Inter, sans-serif",
            fontWeight: 800,
            fontSize: 72,
            color: "rgb(236 239 244)",
            letterSpacing: "-0.03em",
            lineHeight: 1,
          }}
        >
          Sky<span style={{ color: "rgb(148 176 136)" }}>Herd</span>
        </div>
        <div
          style={{
            fontFamily: "Inter, sans-serif",
            fontWeight: 500,
            fontSize: 16,
            color: "rgb(168 180 198)",
            letterSpacing: "0.35em",
            textTransform: "uppercase",
          }}
        >
          Engine · v1.0
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── Beat 5: Hold + fade to Act 2 (frames 720–750, 1 s) ───────────────────────
const Beat5Hold = () => {
  const frame = useCurrentFrame();
  const fadeOut = interpolate(frame, [0, 30], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill
      style={{ backgroundColor: "rgb(6 8 12)", opacity: 1 - fadeOut * 0 }}
    >
      <AbsoluteFill
        style={{
          backgroundColor: "rgb(6 8 12)",
          opacity: 1 - fadeOut,
        }}
      />
    </AbsoluteFill>
  );
};

export const Act1Hook = ({ voDurationsFrames }: Act1Props) => {
  // Fixed-beat lengths in frames:
  const TYPE = 3 * 30; // 90
  const CROSS = 5 * 30; // 150 (ends at 240)
  const GEORGE = Math.max(10 * 30, voDurationsFrames.georgeHook + 60); // >=300
  const PITCH = 6 * 30; // 180
  const HOLD = 1 * 30; // 30

  return (
    <AbsoluteFill>
      <Sequence from={0} durationInFrames={TYPE} layout="none">
        <Beat1Typewriter />
      </Sequence>
      <Sequence from={TYPE} durationInFrames={CROSS} layout="none">
        <Beat2Crossfade />
      </Sequence>
      <Sequence from={TYPE + CROSS} durationInFrames={GEORGE} layout="none">
        <Beat3George voDurationsFrames={voDurationsFrames} />
      </Sequence>
      <Sequence
        from={TYPE + CROSS + GEORGE}
        durationInFrames={PITCH}
        layout="none"
      >
        <Beat4Pitch />
      </Sequence>
      <Sequence
        from={TYPE + CROSS + GEORGE + PITCH}
        durationInFrames={HOLD}
        layout="none"
      >
        <Beat5Hold />
      </Sequence>
    </AbsoluteFill>
  );
};
