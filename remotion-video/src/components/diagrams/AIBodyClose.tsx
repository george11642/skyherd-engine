/**
 * AIBodyClose — Scene 2:32–2:55 (23s / 690 frames @ 30fps)
 *
 * Drone thermal background (t1-pexels-drone-thermal.mp4) with slow zoom-out.
 * Kinetic captions follow the VO close line.
 * Background fades to dark; wordmark fades up: "SkyHerd · Built with Opus 4.7"
 */
import {
  AbsoluteFill,
  interpolate,
  OffthreadVideo,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const CREAM = "rgb(245 240 230)";
const SAGE = "rgb(148 176 136)";
const MONO = "ui-monospace, 'JetBrains Mono', monospace";
const SERIF = "Georgia, 'Times New Roman', serif";

// Caption lines with relative appear times (frames @ 30fps)
const CAPTION_LINES = [
  { text: "And the future of AI?", appearFrame: 15,  size: 62 },
  { text: "It's not just chat windows.", appearFrame: 75,  size: 54 },
  { text: "It's AI that can see, that can act,", appearFrame: 150, size: 46 },
  { text: "that has a body in the world —", appearFrame: 220, size: 46 },
  { text: "watching the things people can't.", appearFrame: 300, size: 44 },
];

// Wordmark fades in late
const WORDMARK_START = 440;
const DARK_FADE_START = 400;
const DARK_FADE_END = 480;

// Slow zoom: scale goes from 1.0 to 1.12 over the whole scene
const ZOOM_END = 690;

export const AIBodyClose: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const fadeIn = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Slow zoom-out on the video
  const videoScale = interpolate(frame, [0, ZOOM_END], [1.12, 1.0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Dark overlay grows over time, fully dark by frame DARK_FADE_END
  const darkOverlay = interpolate(frame, [DARK_FADE_START, DARK_FADE_END], [0, 0.92], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Wordmark
  const wordmarkOpacity = interpolate(frame, [WORDMARK_START, WORDMARK_START + 40], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "#0a0b0c", opacity: fadeIn }}>
      {/* Drone thermal video */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          overflow: "hidden",
          transform: `scale(${videoScale})`,
          transformOrigin: "center center",
        }}
      >
        <OffthreadVideo
          src={staticFile("broll/t1-pexels-drone-thermal.mp4")}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
          volume={0}
          startFrom={0}
          muted
        />
      </div>

      {/* Thermal green tint overlay */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: "linear-gradient(180deg, rgba(0,40,20,0.35) 0%, rgba(0,20,10,0.55) 100%)",
          mixBlendMode: "multiply",
          opacity: interpolate(frame, [0, 60], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      />

      {/* Dark fade overlay */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundColor: "#0a0b0c",
          opacity: darkOverlay,
        }}
      />

      {/* Caption lines (kinetic, fade in/out individually) */}
      {frame < DARK_FADE_END && CAPTION_LINES.map((line, i) => {
        // Each line fades in and then fades out before next line appears
        const nextAppear = CAPTION_LINES[i + 1]?.appearFrame ?? DARK_FADE_START;
        const fadeOutStart = nextAppear - 15;

        const sp = spring({
          frame: frame - line.appearFrame,
          fps,
          config: { damping: 80, stiffness: 120, mass: 1.1 },
        });
        const slideY = interpolate(sp, [0, 1], [40, 0]);
        const fadeInOpacity = interpolate(sp, [0, 0.05, 1], [0, 0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        const fadeOutOpacity = interpolate(
          frame,
          [fadeOutStart, nextAppear],
          [1, 0],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
        );

        // Only show the current / most recent line
        const isLatest = CAPTION_LINES.slice(i + 1).every(
          (l) => frame < l.appearFrame,
        );
        if (!isLatest) return null;

        return (
          <div
            key={`caption-${i}`}
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              bottom: 160,
              textAlign: "center",
              padding: "0 10%",
              transform: `translateY(${slideY}px)`,
              opacity: Math.min(fadeInOpacity, fadeOutOpacity),
            }}
          >
            <div
              style={{
                fontFamily: SERIF,
                fontWeight: 700,
                fontSize: line.size,
                color: CREAM,
                letterSpacing: "-0.015em",
                lineHeight: 1.15,
                textShadow: "0 4px 32px rgba(0,0,0,0.8), 0 0 60px rgba(0,200,80,0.15)",
              }}
            >
              {line.text}
            </div>
          </div>
        );
      })}

      {/* Wordmark */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          opacity: wordmarkOpacity,
        }}
      >
        <div
          style={{
            fontFamily: SERIF,
            fontWeight: 700,
            fontSize: 88,
            color: CREAM,
            letterSpacing: "-0.02em",
            lineHeight: 1,
            textShadow: "0 4px 40px rgba(0,0,0,0.6)",
          }}
        >
          SkyHerd
        </div>
        <div
          style={{
            fontFamily: MONO,
            fontSize: 22,
            color: SAGE,
            letterSpacing: "0.22em",
            textTransform: "uppercase",
            marginTop: 18,
          }}
        >
          Built with Opus 4.7
        </div>
        <div
          style={{
            fontFamily: MONO,
            fontSize: 16,
            color: "rgba(245,240,230,0.5)",
            letterSpacing: "0.1em",
            marginTop: 24,
            opacity: interpolate(frame, [WORDMARK_START + 60, WORDMARK_START + 100], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
          }}
        >
          github.com/george11642/skyherd-engine
        </div>
      </div>
    </AbsoluteFill>
  );
};
