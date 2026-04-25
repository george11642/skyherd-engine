/**
 * NervousSystemStack v2 — Scene 0:35–0:52 (17s / 510 frames @ 30fps)
 *
 * Vertical 5-layer stack: SENSORS → EDGE → AGENT MESH → ACTION → TRUST
 * Agent mesh row: 5 agent CARDS with rolling tool-call snippets.
 * Larger labels, faster fade-in (starts at 30% opacity).
 * Pulse animation flows sensor→edge→agent→action→trust after stack builds.
 * Cost ticker at bottom in larger type.
 */
import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

const CREAM      = "rgb(245 240 230)";
const SAGE       = "rgb(148 176 136)";
const SAGE_LIGHT = "rgb(190 210 180)";
const TERRACOTTA = "rgb(188 90 60)";
const SKY        = "rgb(120 180 220)";
const INK        = "rgb(45 42 38)";
const INK_LIGHT  = "rgb(90 86 80)";
const MONO       = "ui-monospace, 'JetBrains Mono', monospace";
const SERIF      = "Georgia, 'Times New Roman', serif";

const LAYERS = [
  {
    id: "sensors",
    label: "SENSORS",
    sub: "LoRaWAN · Camera · GPS · Pressure",
    color: SKY,
  },
  {
    id: "edge",
    label: "EDGE",
    sub: "Raspberry Pi · MegaDetector V6",
    color: SAGE,
  },
  {
    id: "mesh",
    label: "AGENT MESH",
    sub: null,
    color: TERRACOTTA,
  },
  {
    id: "action",
    label: "ACTION",
    sub: "SMS · Drone dispatch · Twilio voice",
    color: "rgb(210 178 138)",
  },
  {
    id: "trust",
    label: "TRUST",
    sub: "Ed25519 ledger · replay-safe attestation",
    color: "rgb(180 200 160)",
  },
] as const;

// ─── Agent cards ────────────────────────────────────────────────────────────
const AGENTS: Array<{ short: string; call: string }> = [
  {
    short: "FenceLine\nDispatcher",
    call:  "classify_breach({\n  thermal_id:\n  'fence-S-04'\n})",
  },
  {
    short: "HerdHealth\nWatcher",
    call:  "flag_anomaly({\n  cow_id: 'A014',\n  sign: 'lethargy'\n})",
  },
  {
    short: "Predator\nLearner",
    call:  "cross_reference\n_thermal({\n  clip: 'clip-019'\n})",
  },
  {
    short: "Grazing\nOptimizer",
    call:  "compute_rotation({\n  paddock: 'SE-3',\n  pressure: 0.62\n})",
  },
  {
    short: "Calving\nWatch",
    call:  "priority_page({\n  cow: '117',\n  stage: 'labor'\n})",
  },
];

// Staggered layer appear frames
const LAYER_APPEAR = [0, 45, 88, 138, 185] as const;
// Pulse wave starts after all layers are built
const PULSE_START = 230;
// Agents activate staggered after mesh layer appears
const AGENT_ACTIVATE_START = 110;
const AGENT_STAGGER = 32; // frames between each agent card activation

export const NervousSystemStack: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  // Fade-in: start at 30% to avoid dim-stall on first frame
  const fadeIn = interpolate(frame, [0, 10], [0.30, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Pulse wave index (cycles through layers)
  const pulseT = frame > PULSE_START
    ? ((frame - PULSE_START) / (fps * 1.1)) % LAYERS.length
    : -1;

  // Stack geometry — fill more vertical space
  const TITLE_H = 90;
  const COST_H  = 56;
  const stackTop = TITLE_H + 12;
  const stackBottom = height - COST_H - 20;
  const totalH = stackBottom - stackTop;
  const layerGap = 6;
  const layerH = (totalH - layerGap * (LAYERS.length - 1)) / LAYERS.length;
  const layerW = Math.min(width * 0.88, 1100);
  const layerX = (width - layerW) / 2;

  // Cost line opacity
  const costOp = interpolate(frame, [210, 245], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: CREAM, opacity: fadeIn }}>
      {/* ── Title ── */}
      <div style={{
        position: "absolute",
        top: 28,
        left: 0,
        right: 0,
        textAlign: "center",
        fontFamily: SERIF,
        fontWeight: 700,
        fontSize: 44,
        color: INK,
        letterSpacing: "-0.01em",
      }}>
        SkyHerd — Ranch Nervous System
      </div>

      {/* ── Layer rows ── */}
      {LAYERS.map((layer, i) => {
        const appearFrame = LAYER_APPEAR[i];
        const sp = spring({
          frame: frame - appearFrame,
          fps,
          config: { damping: 115, stiffness: 190, mass: 0.65 },
        });
        const slideX = interpolate(sp, [0, 1], [-90, 0]);
        const rowOp  = interpolate(sp, [0, 0.02, 1], [0, 0, 1], {
          extrapolateLeft: "clamp", extrapolateRight: "clamp",
        });

        // Pulse highlight
        const pulseDist = Math.abs(pulseT - i);
        const pulseGlow = pulseT >= 0
          ? interpolate(pulseDist, [0, 0.55, 1.4], [1, 0.4, 0], {
              extrapolateLeft: "clamp", extrapolateRight: "clamp",
            })
          : 0;

        const rowTop = stackTop + i * (layerH + layerGap);
        const isMesh = layer.id === "mesh";

        // Parse color components for rgba usage
        const colorStr = layer.color;

        return (
          <div
            key={layer.id}
            style={{
              position: "absolute",
              left: layerX + slideX,
              top: rowTop,
              width: layerW,
              height: layerH,
              backgroundColor: `rgba(45,42,38,0.05)`,
              border: `2px solid`,
              borderColor: pulseGlow > 0.05
                ? layer.color.replace("rgb(", "rgba(").replace(")", `, ${0.35 + pulseGlow * 0.65})`)
                : "rgba(148,176,136,0.25)",
              borderRadius: 14,
              display: "flex",
              alignItems: "center",
              padding: isMesh ? "0 20px" : "0 28px",
              gap: 20,
              opacity: rowOp,
              boxShadow: pulseGlow > 0.08
                ? `0 0 ${Math.round(28 * pulseGlow)}px ${layer.color.replace("rgb(", "rgba(").replace(")", `, ${pulseGlow * 0.3})`)}`
                : "none",
            }}
          >
            {/* Color stripe */}
            <div style={{
              width: 6,
              height: layerH * 0.62,
              borderRadius: 3,
              backgroundColor: colorStr,
              flexShrink: 0,
              opacity: 0.82 + pulseGlow * 0.18,
            }} />

            {/* Label + sub */}
            <div style={{ flex: isMesh ? "0 0 auto" : 1, minWidth: isMesh ? 170 : undefined }}>
              <div style={{
                fontFamily: MONO,
                fontSize: 20,
                fontWeight: 800,
                color: INK,
                letterSpacing: "0.20em",
                textTransform: "uppercase",
                marginBottom: 5,
              }}>
                {layer.label}
              </div>
              {layer.sub && (
                <div style={{
                  fontFamily: MONO,
                  fontSize: 14,
                  color: INK_LIGHT,
                  letterSpacing: "0.06em",
                }}>
                  {layer.sub}
                </div>
              )}
            </div>

            {/* Agent cards — mesh row only */}
            {isMesh && (
              <div style={{
                flex: 1,
                display: "flex",
                alignItems: "stretch",
                gap: 8,
                justifyContent: "flex-end",
                overflow: "hidden",
              }}>
                {AGENTS.map((agent, ai) => {
                  const activateAt = AGENT_ACTIVATE_START + ai * AGENT_STAGGER;
                  const cardSp = spring({
                    frame: frame - activateAt,
                    fps,
                    config: { damping: 90, stiffness: 240 },
                  });
                  const cardScale = interpolate(cardSp, [0, 1], [0, 1], {
                    extrapolateLeft: "clamp", extrapolateRight: "clamp",
                  });
                  const cardOp = interpolate(cardSp, [0, 0.04, 1], [0, 0, 1], {
                    extrapolateLeft: "clamp", extrapolateRight: "clamp",
                  });
                  // Tool call text scrolls in 8 frames after card appears
                  const callOp = interpolate(frame, [activateAt + 8, activateAt + 18], [0, 1], {
                    extrapolateLeft: "clamp", extrapolateRight: "clamp",
                  });

                  // Highlight: each agent pulses in turn (1s each, after all agents appear)
                  const highlightCycle = frame > PULSE_START
                    ? Math.floor((frame - PULSE_START) / fps) % AGENTS.length
                    : -1;
                  const isHighlighted = highlightCycle === ai;

                  const cardW = Math.floor((layerW - 170 - 60 - 8 * (AGENTS.length - 1)) / AGENTS.length);

                  return (
                    <div
                      key={agent.short}
                      style={{
                        width: cardW,
                        height: layerH - 16,
                        borderRadius: 10,
                        backgroundColor: isHighlighted
                          ? "rgba(188,90,60,0.14)"
                          : "rgba(45,42,38,0.07)",
                        border: `1.5px solid ${isHighlighted ? TERRACOTTA : "rgba(148,176,136,0.3)"}`,
                        display: "flex",
                        flexDirection: "column",
                        padding: "6px 8px",
                        gap: 4,
                        transform: `scale(${cardScale})`,
                        opacity: cardOp,
                        boxShadow: isHighlighted
                          ? `0 0 12px rgba(188,90,60,0.25)`
                          : "none",
                        overflow: "hidden",
                        flexShrink: 0,
                      }}
                    >
                      {/* Agent short name */}
                      <div style={{
                        fontFamily: MONO,
                        fontSize: 10,
                        fontWeight: 800,
                        color: isHighlighted ? TERRACOTTA : INK,
                        letterSpacing: "0.08em",
                        lineHeight: 1.3,
                        whiteSpace: "pre",
                      }}>
                        {agent.short}
                      </div>

                      {/* Divider */}
                      <div style={{
                        height: 1,
                        backgroundColor: isHighlighted
                          ? "rgba(188,90,60,0.35)"
                          : "rgba(148,176,136,0.25)",
                        width: "100%",
                      }} />

                      {/* Rolling tool call */}
                      <div style={{
                        fontFamily: MONO,
                        fontSize: 9,
                        color: isHighlighted ? TERRACOTTA : INK_LIGHT,
                        lineHeight: 1.35,
                        opacity: callOp,
                        whiteSpace: "pre",
                        overflow: "hidden",
                      }}>
                        {agent.call}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Data-flow arrow between layers */}
            {i < LAYERS.length - 1 && (
              <div style={{
                position: "absolute",
                bottom: -(layerGap + 2),
                left: "50%",
                transform: "translateX(-50%)",
                width: 0,
                height: 0,
                borderLeft: "10px solid transparent",
                borderRight: "10px solid transparent",
                borderTop: `${layerGap + 4}px solid ${pulseGlow > 0.1 ? SAGE : SAGE_LIGHT}`,
                opacity: rowOp,
                zIndex: 1,
              }} />
            )}
          </div>
        );
      })}

      {/* ── Cost ticker ── */}
      <div style={{
        position: "absolute",
        bottom: 22,
        left: 0,
        right: 0,
        textAlign: "center",
        fontFamily: MONO,
        fontSize: 22,
        fontWeight: 700,
        color: TERRACOTTA,
        letterSpacing: "0.10em",
        textTransform: "uppercase",
        opacity: costOp,
      }}>
        $4.17 / week · 5 agents · idle-pause billing
      </div>
    </AbsoluteFill>
  );
};
