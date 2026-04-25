/**
 * NervousSystemStack — Scene 0:35–0:52 (17s / 510 frames @ 30fps)
 *
 * Vertical 5-layer stack: SENSORS → EDGE → AGENT MESH → ACTION → TRUST
 * Each layer fades in staggered. Pulse animation after full stack is built.
 * Agent mesh layer shows 5 named agent dots with brief highlights.
 */
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

const CREAM = "rgb(245 240 230)";
const SAGE = "rgb(148 176 136)";
const SAGE_LIGHT = "rgb(190 210 180)";
const TERRACOTTA = "rgb(188 90 60)";
const INK = "rgb(45 42 38)";
const INK_LIGHT = "rgb(90 86 80)";
const MONO = "ui-monospace, 'JetBrains Mono', monospace";
const SERIF = "Georgia, 'Times New Roman', serif";

const LAYERS = [
  { id: "sensors", label: "SENSORS", sub: "LoRaWAN · Camera · GPS · Trough", color: "rgb(120 180 220)" },
  { id: "edge",    label: "EDGE",    sub: "Raspberry Pi · MegaDetector V6",  color: SAGE },
  { id: "mesh",    label: "AGENT MESH", sub: null,                            color: "rgb(188 90 60)" },
  { id: "action",  label: "ACTION",  sub: "SMS · Drone · Voice · Twilio",    color: "rgb(210 178 138)" },
  { id: "trust",   label: "TRUST",   sub: "Ed25519 ledger · replay-safe",    color: "rgb(180 200 160)" },
];

const AGENTS = [
  "FenceLineDispatcher",
  "HerdHealthWatcher",
  "PredatorPatternLearner",
  "GrazingOptimizer",
  "CalvingWatch",
];

// Each layer appears at staggered frames
const LAYER_APPEAR = [0, 40, 80, 130, 175];
// Pulse wave start (after all layers built)
const PULSE_START = 220;
// Agent highlight cycle starts at frame 270
const AGENT_HIGHLIGHT_START = 270;

export const NervousSystemStack: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const fadeIn = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Pulse wave: a value 0..4 that cycles through layers
  const pulseT = frame > PULSE_START
    ? ((frame - PULSE_START) / (fps * 1.2)) % LAYERS.length
    : -1;

  // Active agent highlight index
  const agentT = frame > AGENT_HIGHLIGHT_START
    ? Math.floor(((frame - AGENT_HIGHLIGHT_START) / fps) * 1.2) % AGENTS.length
    : -1;

  const stackTop = 140;
  const stackBottom = height - 100;
  const layerHeight = (stackBottom - stackTop) / LAYERS.length;
  const layerGap = 8;
  const layerW = Math.min(width * 0.72, 860);
  const layerX = (width - layerW) / 2;

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
          fontSize: 36,
          color: INK,
          letterSpacing: "-0.01em",
        }}
      >
        SkyHerd — Ranch Nervous System
      </div>

      {/* Layers */}
      {LAYERS.map((layer, i) => {
        const appearFrame = LAYER_APPEAR[i];
        const sp = spring({
          frame: frame - appearFrame,
          fps,
          config: { damping: 110, stiffness: 180, mass: 0.7 },
        });
        const x = interpolate(sp, [0, 1], [-80, 0]);
        const opacity = interpolate(sp, [0, 0.01, 1], [0, 0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });

        // Pulse highlight: brighten when wave reaches this layer
        const pulseDist = Math.abs(pulseT - i);
        const pulseGlow = pulseT >= 0
          ? interpolate(pulseDist, [0, 0.6, 1.5], [1, 0.5, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            })
          : 0;

        const layerTop = stackTop + i * (layerHeight);
        const h = layerHeight - layerGap;

        const isMesh = layer.id === "mesh";

        return (
          <div
            key={layer.id}
            style={{
              position: "absolute",
              left: layerX + x,
              top: layerTop,
              width: layerW,
              height: h,
              backgroundColor: "rgba(45,42,38,0.06)",
              border: `2px solid ${interpolate(pulseGlow, [0, 1], [0.15, 1] as [number, number])}`,
              borderColor: `rgba(${layer.color.replace(/rgb\(|\)/g, "")}, ${0.3 + pulseGlow * 0.7})`,
              borderRadius: 12,
              display: "flex",
              alignItems: "center",
              padding: "0 28px",
              gap: 24,
              opacity,
              boxShadow: pulseGlow > 0.1
                ? `0 0 ${Math.round(24 * pulseGlow)}px rgba(${layer.color.replace(/rgb\(|\)/g, "")}, ${pulseGlow * 0.35})`
                : "none",
            }}
          >
            {/* Color stripe */}
            <div
              style={{
                width: 5,
                height: h * 0.6,
                borderRadius: 3,
                backgroundColor: layer.color,
                flexShrink: 0,
                opacity: 0.85 + pulseGlow * 0.15,
              }}
            />

            {/* Label + sub */}
            <div style={{ flex: isMesh ? "0 0 auto" : 1 }}>
              <div
                style={{
                  fontFamily: MONO,
                  fontSize: isMesh ? 17 : 15,
                  fontWeight: 800,
                  color: INK,
                  letterSpacing: "0.18em",
                  textTransform: "uppercase",
                  marginBottom: 4,
                }}
              >
                {layer.label}
              </div>
              {layer.sub && (
                <div
                  style={{
                    fontFamily: MONO,
                    fontSize: 12,
                    color: INK_LIGHT,
                    letterSpacing: "0.06em",
                  }}
                >
                  {layer.sub}
                </div>
              )}
            </div>

            {/* Agent mesh dots */}
            {isMesh && (
              <div
                style={{
                  flex: 1,
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  justifyContent: "flex-end",
                  flexWrap: "wrap",
                }}
              >
                {AGENTS.map((name, ai) => {
                  const isHighlighted = ai === agentT;
                  const dotSp = spring({
                    frame: frame - (LAYER_APPEAR[2] + ai * 12),
                    fps,
                    config: { damping: 100, stiffness: 220 },
                  });
                  const dotScale = interpolate(dotSp, [0, 1], [0, 1], {
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                  });
                  return (
                    <div
                      key={name}
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        gap: 3,
                        transform: `scale(${dotScale})`,
                      }}
                    >
                      <div
                        style={{
                          width: isHighlighted ? 20 : 14,
                          height: isHighlighted ? 20 : 14,
                          borderRadius: "50%",
                          backgroundColor: isHighlighted ? TERRACOTTA : SAGE,
                          boxShadow: isHighlighted
                            ? `0 0 14px ${TERRACOTTA}`
                            : "none",
                          transition: "none",
                        }}
                      />
                      <div
                        style={{
                          fontFamily: MONO,
                          fontSize: 8,
                          color: isHighlighted ? TERRACOTTA : INK_LIGHT,
                          letterSpacing: "0.04em",
                          textAlign: "center",
                          maxWidth: 80,
                          wordBreak: "break-word",
                          lineHeight: 1.2,
                          fontWeight: isHighlighted ? 800 : 500,
                        }}
                      >
                        {name.replace(/([A-Z])/g, " $1").trim()}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Data flow arrow between layers */}
            {i < LAYERS.length - 1 && (
              <div
                style={{
                  position: "absolute",
                  bottom: -layerGap - 2,
                  left: "50%",
                  transform: "translateX(-50%)",
                  width: 0,
                  height: 0,
                  borderLeft: "8px solid transparent",
                  borderRight: "8px solid transparent",
                  borderTop: `${layerGap + 2}px solid ${SAGE_LIGHT}`,
                  opacity: opacity,
                  zIndex: 1,
                }}
              />
            )}
          </div>
        );
      })}

      {/* Cost callout */}
      <div
        style={{
          position: "absolute",
          bottom: 28,
          right: 80,
          fontFamily: MONO,
          fontSize: 14,
          color: TERRACOTTA,
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          opacity: interpolate(frame, [200, 240], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        $4.17 / week · Opus 4.7 · 5 agents
      </div>
    </AbsoluteFill>
  );
};
