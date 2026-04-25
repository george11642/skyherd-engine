/**
 * v2 — Variants A & B Act 2 (Demo, 90s).
 *
 * Five-scenario montage (~11s each = 55s) + "under the hood" mesh reveal (35s).
 * Same skeleton for both variants — no divergence.
 */
import {
  AbsoluteFill,
  Audio,
  Sequence,
  Series,
  Video,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { AB_LAYOUT } from "../../compositions/calculate-main-metadata";
import {
  ACCENT_MAP,
  type Accent,
  AnchorChip,
  LowerThird,
  useFadeInOut,
} from "./shared";

const FPS = 30;

// ── Scenario beat ────────────────────────────────────────────────────────────
type ScenarioProps = {
  scenarioNumber: number;
  clipName: string;
  voFile: string | null;
  voStartFrame: number;
  agent: string;
  detail: string;
  accent: Accent;
  anchorLabel: string;
  anchorTopic: string;
  anchorHash: string;
  anchorStatus: string;
};

const ScenarioBeat = ({
  scenarioNumber,
  clipName,
  voFile,
  voStartFrame,
  agent,
  detail,
  accent,
  anchorLabel,
  anchorTopic,
  anchorHash,
  anchorStatus,
}: ScenarioProps) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const fadeIn = interpolate(frame, [0, 10], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 14, durationInFrames],
    [1, 0.25],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const opacity = Math.min(fadeIn, fadeOut);

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(6 8 12)" }}>
      <div style={{ width: "100%", height: "100%", opacity }}>
        <Video
          src={staticFile(`clips/${clipName}`)}
          startFrom={0}
          endAt={420}
          muted
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
      </div>
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(6,8,12,0.55) 100%)",
          opacity,
        }}
      />

      {/* Scenario badge top-left */}
      <div
        style={{
          position: "absolute",
          top: 90,
          left: 90,
          display: "flex",
          alignItems: "center",
          gap: 16,
          opacity: fadeIn,
        }}
      >
        <div
          style={{
            width: 56,
            height: 56,
            borderRadius: 28,
            backgroundColor: ACCENT_MAP[accent],
            color: "rgb(10 12 16)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: "Inter, sans-serif",
            fontWeight: 800,
            fontSize: 28,
          }}
        >
          {scenarioNumber}
        </div>
        <div
          style={{
            fontFamily: "Inter, sans-serif",
            fontSize: 16,
            letterSpacing: "0.32em",
            textTransform: "uppercase",
            color: "rgb(236 239 244)",
            fontWeight: 600,
          }}
        >
          Scenario {scenarioNumber} / 5
        </div>
      </div>

      {voFile ? (
        <Sequence from={voStartFrame}>
          <Audio src={staticFile(voFile)} />
        </Sequence>
      ) : null}

      <LowerThird
        agent={agent}
        detail={detail}
        accent={accent}
        appearFrame={45}
        durationInFrames={durationInFrames - 45}
      />
      <AnchorChip
        label={anchorLabel}
        topic={anchorTopic}
        hash={anchorHash}
        statusPill={anchorStatus}
        appearFrame={Math.max(150, voStartFrame + 30)}
        accent={accent}
      />
    </AbsoluteFill>
  );
};

// ── Mesh "under the hood" reveal (35s) ───────────────────────────────────────
//
// Animated 5-agent node canvas with smooth camera pan. Mirrors CrossBeam's
// Opus Orchestrator beat (the top-3-confirmed copyable moment).
type AgentNode = {
  id: string;
  label: string;
  x: number;
  y: number;
  accent: Accent;
};

const MESH_NODES: AgentNode[] = [
  { id: "fence", label: "FenceLineDispatcher", x: -380, y: -180, accent: "thermal" },
  { id: "health", label: "HerdHealthWatcher", x: 380, y: -180, accent: "warn" },
  { id: "predator", label: "PredatorPatternLearner", x: -480, y: 0, accent: "sky" },
  { id: "grazing", label: "GrazingOptimizer", x: 480, y: 0, accent: "sage" },
  { id: "calving", label: "CalvingWatch", x: 0, y: 220, accent: "dust" },
];

const MeshBeat = () => {
  const frame = useCurrentFrame();
  const { durationInFrames, fps } = useVideoConfig();
  const opacity = useFadeInOut(durationInFrames, 30, 35);

  // Smooth camera pan: starts centered, drifts right, then converges back.
  const pan = interpolate(
    frame,
    [0, durationInFrames * 0.5, durationInFrames],
    [0, 80, 0],
  );

  // Center pulse expands outward through the run.
  const pulseProgress = (frame % 90) / 90;
  const pulseR = 60 + pulseProgress * 360;
  const pulseO = 1 - pulseProgress;

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(8 10 14)", opacity }}>
      <Audio src={staticFile("voiceover/vo-mesh.mp3")} />

      {/* Title strip top-left */}
      <div
        style={{
          position: "absolute",
          top: 80,
          left: 90,
          fontFamily: "Inter, sans-serif",
          opacity: useFadeInOut(durationInFrames, 25, 25),
        }}
      >
        <div
          style={{
            fontSize: 14,
            color: ACCENT_MAP.sage,
            letterSpacing: "0.34em",
            textTransform: "uppercase",
            fontWeight: 600,
            marginBottom: 12,
          }}
        >
          Under the hood · Managed Agents mesh
        </div>
        <div
          style={{
            fontSize: 44,
            fontWeight: 700,
            color: "rgb(236 239 244)",
            letterSpacing: "-0.018em",
          }}
        >
          Five sessions. Idle until called.
        </div>
      </div>

      {/* Node canvas */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          transform: `translateX(${-pan}px)`,
        }}
      >
        <svg
          width="100%"
          height="100%"
          viewBox="-960 -540 1920 1080"
          preserveAspectRatio="xMidYMid meet"
        >
          {/* Edges from center to each agent */}
          {MESH_NODES.map((n, i) => {
            const edgeAppear = 60 + i * 18;
            const edgeP = spring({
              frame: frame - edgeAppear,
              fps,
              config: { damping: 100, stiffness: 200 },
            });
            return (
              <line
                key={`edge-${n.id}`}
                x1={0}
                y1={0}
                x2={n.x * edgeP}
                y2={n.y * edgeP}
                stroke={ACCENT_MAP[n.accent]}
                strokeWidth={2}
                strokeOpacity={0.55 * edgeP}
                strokeDasharray="4 6"
              />
            );
          })}
          {/* Pulse ring */}
          <circle
            cx={0}
            cy={0}
            r={pulseR}
            fill="none"
            stroke={ACCENT_MAP.sage}
            strokeWidth={2}
            strokeOpacity={pulseO * 0.55}
          />
          {/* Center node */}
          <circle
            cx={0}
            cy={0}
            r={42}
            fill="rgb(16 19 25)"
            stroke={ACCENT_MAP.sage}
            strokeWidth={3}
          />
          <text
            x={0}
            y={6}
            textAnchor="middle"
            fontFamily="Inter, sans-serif"
            fontSize={14}
            fontWeight={700}
            fill="rgb(236 239 244)"
          >
            EVENT
          </text>
          {/* Agent nodes */}
          {MESH_NODES.map((n, i) => {
            const nodeAppear = 90 + i * 18;
            const np = spring({
              frame: frame - nodeAppear,
              fps,
              config: { damping: 100, stiffness: 220 },
            });
            const scale = interpolate(np, [0, 1], [0, 1]);
            return (
              <g key={`node-${n.id}`} transform={`translate(${n.x} ${n.y}) scale(${scale})`}>
                <rect
                  x={-130}
                  y={-26}
                  width={260}
                  height={52}
                  rx={26}
                  fill="rgb(16 19 25)"
                  stroke={ACCENT_MAP[n.accent]}
                  strokeWidth={2}
                />
                <text
                  x={0}
                  y={6}
                  textAnchor="middle"
                  fontFamily="Inter, sans-serif"
                  fontSize={16}
                  fontWeight={600}
                  fill="rgb(236 239 244)"
                >
                  {n.label}
                </text>
              </g>
            );
          })}
          {/* Merkle chain visualization (appears late) */}
          {(() => {
            const chainAppear = 540;
            const cp = spring({
              frame: frame - chainAppear,
              fps,
              config: { damping: 100, stiffness: 150 },
            });
            const chainO = interpolate(cp, [0, 1], [0, 1]);
            return (
              <g opacity={chainO} transform="translate(0 380)">
                {Array.from({ length: 8 }).map((_, i) => (
                  <rect
                    key={`block-${i}`}
                    x={-220 + i * 56}
                    y={-12}
                    width={48}
                    height={24}
                    rx={3}
                    fill="rgb(16 19 25)"
                    stroke={ACCENT_MAP.sage}
                    strokeWidth={1.5}
                  />
                ))}
                <text
                  x={0}
                  y={-30}
                  textAnchor="middle"
                  fontFamily="Inter, sans-serif"
                  fontSize={12}
                  fontWeight={700}
                  fill={ACCENT_MAP.sage}
                  letterSpacing={4}
                >
                  ED25519 · 360 SIGNED EVENTS
                </text>
              </g>
            );
          })()}
        </svg>
      </div>

      {/* Cost ticker bottom-right (callback to hook for B; reveal for A) */}
      <div
        style={{
          position: "absolute",
          bottom: 80,
          right: 100,
          fontFamily: "ui-monospace, JetBrains Mono, monospace",
          fontSize: 28,
          fontWeight: 600,
          color: ACCENT_MAP.dust,
          opacity: interpolate(frame, [630, 690], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
          backgroundColor: "rgba(16,19,25,0.82)",
          border: `1px solid ${ACCENT_MAP.dust}`,
          padding: "10px 18px",
          borderRadius: 6,
          letterSpacing: "0.04em",
        }}
      >
        cost · $4.17 / week
      </div>

      {/* Closing emphasis caption */}
      <div
        style={{
          position: "absolute",
          bottom: 160,
          left: "50%",
          transform: "translateX(-50%)",
          fontFamily: "Inter, sans-serif",
          fontSize: 32,
          fontWeight: 700,
          color: "rgb(236 239 244)",
          letterSpacing: "-0.012em",
          opacity: interpolate(frame, [840, 900], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
          textShadow: "0 6px 24px rgba(0,0,0,0.7)",
        }}
      >
        Same seed. Same bytes. Every time.
      </div>
    </AbsoluteFill>
  );
};

// ── Act 2 root ───────────────────────────────────────────────────────────────
export const ABAct2Demo = () => {
  const SCENARIO = AB_LAYOUT.act2.scenarioSeconds * FPS; // 330
  const MESH = AB_LAYOUT.act2.meshSeconds * FPS; // 1050

  return (
    <AbsoluteFill>
      <Series>
        <Series.Sequence durationInFrames={SCENARIO}>
          <ScenarioBeat
            scenarioNumber={1}
            clipName="coyote.mp4"
            voFile="voiceover/vo-coyote.mp3"
            voStartFrame={120}
            agent="FenceLineDispatcher"
            detail="Coyote · 91% confidence · Fence W-12 · Mavic dispatched"
            accent="thermal"
            anchorLabel="Attest row"
            anchorTopic="Fence W-12 breach"
            anchorHash="a7c3…f91e"
            anchorStatus="Signed"
          />
        </Series.Sequence>
        <Series.Sequence durationInFrames={SCENARIO}>
          <ScenarioBeat
            scenarioNumber={2}
            clipName="sick_cow.mp4"
            voFile="voiceover/vo-sick-cow.mp3"
            voStartFrame={120}
            agent="HerdHealthWatcher"
            detail="Cow A014 · pinkeye 83% · Vet packet generated"
            accent="warn"
            anchorLabel="Vet packet"
            anchorTopic="Cow A014 · pinkeye"
            anchorHash="4d82…b03c"
            anchorStatus="Sent"
          />
        </Series.Sequence>
        <Series.Sequence durationInFrames={SCENARIO}>
          <ScenarioBeat
            scenarioNumber={3}
            clipName="water.mp4"
            voFile={null}
            voStartFrame={0}
            agent="GrazingOptimizer"
            detail="Tank 7 pressure drop · IR flyover scheduled"
            accent="sky"
            anchorLabel="IR flyover"
            anchorTopic="Tank 7 · pressure drop"
            anchorHash="92e1…5a0d"
            anchorStatus="Queued"
          />
        </Series.Sequence>
        <Series.Sequence durationInFrames={SCENARIO}>
          <ScenarioBeat
            scenarioNumber={4}
            clipName="calving.mp4"
            voFile="voiceover/vo-calving.mp3"
            voStartFrame={120}
            agent="CalvingWatch"
            detail="Cow 117 · pre-labor · Rancher paged (priority)"
            accent="sage"
            anchorLabel="Behavior trace"
            anchorTopic="Cow 117 · pre-labor"
            anchorHash="61bf…2c94"
            anchorStatus="Paged"
          />
        </Series.Sequence>
        <Series.Sequence durationInFrames={SCENARIO}>
          <ScenarioBeat
            scenarioNumber={5}
            clipName="storm.mp4"
            voFile="voiceover/vo-storm.mp3"
            voStartFrame={120}
            agent="Weather-Redirect"
            detail="Hail ETA 45 min · Paddock B → Shelter 2"
            accent="dust"
            anchorLabel="Redirect plan"
            anchorTopic="Paddock B → Shelter 2"
            anchorHash="d3a9…7e11"
            anchorStatus="Active"
          />
        </Series.Sequence>
        <Series.Sequence durationInFrames={MESH}>
          <MeshBeat />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};
