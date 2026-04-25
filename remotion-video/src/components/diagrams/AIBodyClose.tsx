/**
 * AIBodyClose — Scene 9 (AIBody / Close) — 23s / 690 frames @ 30fps
 *
 * Mountain b-roll (t1-drone-arid-mountains.mp4) held for the full scene.
 * Faint diagram overlay: sensor-radius rings, agent-node dots, data-flow lines.
 * Kinetic captions for the VO close line (unchanged from v4).
 * Scene ends on the architecture diagram at full opacity — wordmark/credits
 * end-card is owned by CCloseWordmark (next scene), not this component.
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

// ---------------------------------------------------------------------------
// Palette
// ---------------------------------------------------------------------------
const CREAM   = "rgb(245 240 230)";
const SAGE    = "rgb(148 176 136)";
const TERRA   = "rgb(185 110 80)";
const SERIF   = "Georgia, 'Times New Roman', serif";

// ---------------------------------------------------------------------------
// Caption lines — VO unchanged from v4
// ---------------------------------------------------------------------------
const CAPTION_LINES = [
  { text: "And the future of AI?",                   appearFrame:  15, size: 62 },
  { text: "It's not just chat windows.",              appearFrame:  75, size: 54 },
  { text: "It's AI that can see, that can act,",     appearFrame: 150, size: 46 },
  { text: "that has a body in the world —",           appearFrame: 220, size: 46 },
  { text: "watching the things people can't.",        appearFrame: 300, size: 44 },
];

// ---------------------------------------------------------------------------
// Timing constants
// ---------------------------------------------------------------------------
const TOTAL_FRAMES   = 690;   // 23 s
const VO_END_FRAME   = 384;   // ~12.8 s — last caption exits here

// Slow zoom: subtle pull-back over full scene (reads "expansive")
const ZOOM_START_SCALE = 1.10;
const ZOOM_END_SCALE   = 1.0;

// ---------------------------------------------------------------------------
// Diagram overlay seed data (stable — no Math.random in render path)
// ---------------------------------------------------------------------------

interface AgentDot { cx: number; cy: number; r: number; baseOpacity: number; twinklePhase: number }
const AGENT_DOTS: AgentDot[] = [
  { cx:  120, cy: 200, r:  7, baseOpacity: 0.10, twinklePhase: 0.0  },
  { cx:  300, cy: 340, r:  5, baseOpacity: 0.07, twinklePhase: 0.7  },
  { cx:  480, cy: 160, r:  9, baseOpacity: 0.13, twinklePhase: 1.4  },
  { cx:  640, cy: 420, r:  6, baseOpacity: 0.09, twinklePhase: 2.1  },
  { cx:  820, cy: 250, r:  8, baseOpacity: 0.12, twinklePhase: 0.4  },
  { cx:  960, cy: 540, r:  5, baseOpacity: 0.07, twinklePhase: 1.1  },
  { cx: 1100, cy: 180, r:  7, baseOpacity: 0.10, twinklePhase: 2.5  },
  { cx: 1280, cy: 380, r:  9, baseOpacity: 0.14, twinklePhase: 0.9  },
  { cx: 1460, cy: 300, r:  6, baseOpacity: 0.08, twinklePhase: 1.8  },
  { cx: 1600, cy: 500, r:  8, baseOpacity: 0.12, twinklePhase: 3.0  },
  { cx: 1760, cy: 210, r:  5, baseOpacity: 0.07, twinklePhase: 2.3  },
  { cx: 1860, cy: 620, r:  7, baseOpacity: 0.10, twinklePhase: 0.6  },
  { cx:  200, cy: 700, r:  6, baseOpacity: 0.09, twinklePhase: 1.5  },
  { cx:  700, cy: 800, r:  8, baseOpacity: 0.11, twinklePhase: 2.8  },
];

interface DataLine { x1: number; y1: number; x2: number; y2: number; fadePhase: number }
const DATA_LINES: DataLine[] = [
  { x1:  120, y1: 200, x2:  300, y2: 340, fadePhase: 0.0  },
  { x1:  480, y1: 160, x2:  640, y2: 420, fadePhase: 1.2  },
  { x1:  820, y1: 250, x2:  960, y2: 540, fadePhase: 0.5  },
  { x1: 1100, y1: 180, x2: 1280, y2: 380, fadePhase: 2.0  },
  { x1: 1460, y1: 300, x2: 1600, y2: 500, fadePhase: 0.8  },
  { x1:  300, y1: 340, x2:  480, y2: 160, fadePhase: 1.7  },
  { x1:  640, y1: 420, x2:  820, y2: 250, fadePhase: 2.4  },
];

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const DiagramOverlay: React.FC<{ frame: number; diagramOpacity: number }> = ({
  frame,
  diagramOpacity,
}) => {
  // Slow pulse for rings (1 cycle / ~240 frames)
  const ringPulse = 0.5 + 0.5 * Math.sin((frame / 240) * Math.PI * 2);

  return (
    <AbsoluteFill style={{ pointerEvents: "none", opacity: diagramOpacity }}>
      <svg
        width="1920"
        height="1080"
        viewBox="0 0 1920 1080"
        style={{ position: "absolute", inset: 0 }}
      >
        {/* Concentric sensor-radius rings — centered mid-left-of-frame */}
        {[180, 320, 460].map((r, idx) => (
          <circle
            key={`ring-${idx}`}
            cx={960}
            cy={540}
            r={r}
            fill="none"
            stroke={SAGE}
            strokeWidth={1.2}
            opacity={0.08 + 0.03 * ringPulse * (1 - idx * 0.2)}
          />
        ))}

        {/* Data-flow lines — intermittent fade */}
        {DATA_LINES.map((line, idx) => {
          const lineFade =
            0.03 +
            0.025 *
              Math.abs(Math.sin(((frame + line.fadePhase * 60) / 180) * Math.PI));
          return (
            <line
              key={`dline-${idx}`}
              x1={line.x1}
              y1={line.y1}
              x2={line.x2}
              y2={line.y2}
              stroke={SAGE}
              strokeWidth={0.8}
              opacity={lineFade}
            />
          );
        })}

        {/* Agent-node dots — slow twinkle */}
        {AGENT_DOTS.map((dot, idx) => {
          const twinkle =
            dot.baseOpacity +
            0.04 *
              Math.sin(((frame + dot.twinklePhase * 50) / 90) * Math.PI * 2);
          return (
            <circle
              key={`dot-${idx}`}
              cx={dot.cx}
              cy={dot.cy}
              r={dot.r}
              fill={TERRA}
              opacity={Math.max(0, Math.min(0.18, twinkle))}
            />
          );
        })}
      </svg>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export const AIBodyClose: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Scene fade-in
  const fadeIn = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Slow zoom-out on the mountain b-roll
  const videoScale = interpolate(frame, [0, TOTAL_FRAMES], [ZOOM_START_SCALE, ZOOM_END_SCALE], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Diagram overlay fades in early and holds at full opacity through end of scene
  const diagramOpacity = interpolate(
    frame,
    [30, 90],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  return (
    <AbsoluteFill style={{ backgroundColor: "#0a0b0c", opacity: fadeIn }}>
      {/* Mountain b-roll — held for the full 23s, no tail cut */}
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
          src={staticFile("broll/t1-drone-arid-mountains.mp4")}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
          volume={0}
          startFrom={0}
          muted
        />
      </div>

      {/* Subtle warm vignette — frames the mountain footage */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(ellipse at center, transparent 40%, rgba(10,8,6,0.55) 100%)",
          pointerEvents: "none",
        }}
      />

      {/* Diagram overlay — sensor rings, agent dots, data lines */}
      <DiagramOverlay frame={frame} diagramOpacity={diagramOpacity} />

      {/* Kinetic captions — white-with-shadow, large serif, fade-in per word */}
      {frame < VO_END_FRAME &&
        CAPTION_LINES.map((line, i) => {
          const nextAppear = CAPTION_LINES[i + 1]?.appearFrame ?? VO_END_FRAME;
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

          // Only show the current / most-recent line
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
                  textShadow:
                    "0 4px 32px rgba(0,0,0,0.85), 0 0 60px rgba(80,160,100,0.12)",
                }}
              >
                {line.text}
              </div>
            </div>
          );
        })}
    </AbsoluteFill>
  );
};
