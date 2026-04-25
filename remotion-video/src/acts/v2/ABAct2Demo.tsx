/**
 * v2 — Variants A & B Act 2 (Demo, ~90s) — iter2 restructure.
 *
 * Deep coyote scenario (~25s, full VO) + silent 4-scene montage (~25s) +
 * mesh-opus beat (~40s, names Opus 4.7 explicitly). Same skeleton for both
 * variants.
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
import {
  ACCENT_MAP,
  type Accent,
  AnchorChip,
  LowerThird,
  useFadeInOut,
} from "./shared";

const FPS = 30;

// ── Mesh "under the hood" reveal (~40s, iter2) ───────────────────────────────
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
      {/* Bridge cue plays at frame 0 — "Five scenarios. One ranch. Zero humans." */}
      <Audio src={staticFile("voiceover/vo-montage-bridge.mp3")} />
      {/* Main mesh VO starts after bridge (~5s offset) */}
      <Audio src={staticFile("voiceover/vo-mesh-opus.mp3")} startFrom={Math.round(5.07 * FPS)} />

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
          Under the hood · Opus 4.7 · Managed Agents mesh
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

// ── Deep coyote beat (iter2): single scenario, full VO, ~25s ─────────────────
//
// This is the cinematic beat. Scripts call for: thermal pulse → FenceLineDispatcher
// lane flash → drone telemetry → drone POV → deterrent → mock SMS bubble →
// HashChip slide. Visually, the coyote clip carries the footage; overlays pop
// on top at scripted beats.
const DeepCoyoteBeat = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const fadeIn = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 20, durationInFrames],
    [1, 0.25],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const opacity = Math.min(fadeIn, fadeOut);

  // SMS bubble at ~19s mark per script — shows the Wes text pattern
  const SMS_AT = 19 * 30;
  const smsO = interpolate(frame, [SMS_AT, SMS_AT + 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(6 8 12)" }}>
      <Audio src={staticFile("voiceover/vo-coyote-deep.mp3")} />
      <div style={{ width: "100%", height: "100%", opacity }}>
        <Video
          src={staticFile("clips/coyote.mp4")}
          startFrom={0}
          endAt={durationInFrames + 60}
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
            backgroundColor: ACCENT_MAP.thermal,
            color: "rgb(10 12 16)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: "Inter, sans-serif",
            fontWeight: 800,
            fontSize: 22,
          }}
        >
          3:14
        </div>
        <div
          style={{
            fontFamily: "Inter, sans-serif",
            fontSize: 14,
            letterSpacing: "0.32em",
            textTransform: "uppercase",
            color: "rgb(236 239 244)",
            fontWeight: 600,
          }}
        >
          Deep scenario · Coyote at fence
        </div>
      </div>

      <LowerThird
        agent="FenceLineDispatcher"
        detail="Coyote · 91% · Fence W-12 · Mavic dispatched"
        accent="thermal"
        appearFrame={60}
        durationInFrames={durationInFrames - 60}
      />
      <AnchorChip
        label="Attest row"
        topic="Fence W-12 breach"
        hash="a7c3…f91e"
        statusPill="Signed"
        appearFrame={22 * 30}
        accent="thermal"
      />

      {/* Mock SMS bubble bottom-right at 19s */}
      <div
        style={{
          position: "absolute",
          bottom: 240,
          right: 90,
          opacity: smsO,
          maxWidth: 420,
          backgroundColor: "rgba(30,34,40,0.92)",
          borderRadius: 18,
          border: "1px solid rgba(148,176,136,0.3)",
          padding: "14px 18px",
          fontFamily: "Inter, sans-serif",
          color: "rgb(236 239 244)",
          boxShadow: "0 8px 32px rgba(0,0,0,0.55)",
        }}
      >
        <div
          style={{
            fontSize: 11,
            color: "rgb(148 176 136)",
            letterSpacing: "0.28em",
            textTransform: "uppercase",
            fontWeight: 700,
            marginBottom: 6,
          }}
        >
          SMS · 3:14am
        </div>
        <div
          style={{
            fontSize: 16,
            lineHeight: 1.35,
            fontWeight: 500,
          }}
        >
          Coyote on W-12. Drone scared it off. Fence intact. You&rsquo;re good.
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── Montage scene (iter2): 6s fast-cut, kinetic callout + anchor + optional VO
type MontageProps = {
  clipName: string;
  callout: string;
  agent: string;
  detail: string;
  accent: Accent;
  anchorLabel: string;
  anchorTopic: string;
  anchorHash: string;
  anchorStatus: string;
  /** Optional VO file path relative to public/. Plays from frame 0. */
  voFile?: string;
};

const MontageScene = ({
  clipName,
  callout,
  agent,
  detail,
  accent,
  anchorLabel,
  anchorTopic,
  anchorHash,
  anchorStatus,
  voFile,
}: MontageProps) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const fadeIn = interpolate(frame, [0, 6], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 8, durationInFrames],
    [1, 0.2],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const opacity = Math.min(fadeIn, fadeOut);

  // Callout pops in at ~0.5s, holds through the scene.
  const calloutO = interpolate(frame, [15, 30], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const calloutY = interpolate(frame, [15, 30], [20, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(6 8 12)" }}>
      {voFile ? <Audio src={staticFile(voFile)} /> : null}
      <div style={{ width: "100%", height: "100%", opacity }}>
        <Video
          src={staticFile(`clips/${clipName}`)}
          startFrom={0}
          endAt={200}
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
            "radial-gradient(ellipse at center, rgba(0,0,0,0) 50%, rgba(6,8,12,0.65) 100%)",
          opacity,
        }}
      />

      {/* Big kinetic callout — center-top */}
      <div
        style={{
          position: "absolute",
          top: 180,
          left: 0,
          right: 0,
          textAlign: "center",
          padding: "0 8%",
          opacity: calloutO,
          transform: `translateY(${calloutY}px)`,
        }}
      >
        <div
          style={{
            fontFamily: "Inter, sans-serif",
            fontWeight: 800,
            fontSize: 56,
            color: ACCENT_MAP[accent],
            letterSpacing: "-0.022em",
            lineHeight: 1.1,
            textShadow: "0 6px 30px rgba(0,0,0,0.75)",
          }}
        >
          {callout}
        </div>
      </div>

      <LowerThird
        agent={agent}
        detail={detail}
        accent={accent}
        appearFrame={24}
        durationInFrames={durationInFrames - 24}
      />
      <AnchorChip
        label={anchorLabel}
        topic={anchorTopic}
        hash={anchorHash}
        statusPill={anchorStatus}
        appearFrame={45}
        accent={accent}
      />
    </AbsoluteFill>
  );
};

// ── Act 2 root (iter2): deep coyote + 4-scene montage + mesh-opus ────────────
export const ABAct2Demo = () => {
  const DEEP = AB_LAYOUT.act2.coyoteDeepMin * FPS; // 750 (25s * 30)
  const MONTAGE_TOTAL = AB_LAYOUT.act2.montageSeconds * FPS; // 750
  const SCENE = Math.floor(
    MONTAGE_TOTAL / AB_LAYOUT.act2.montageSceneCount,
  ); // ~187 frames
  const MESH = AB_LAYOUT.act2.meshMin * FPS; // 1200 (40s * 30)

  return (
    <AbsoluteFill>
      <Series>
        <Series.Sequence durationInFrames={DEEP}>
          <DeepCoyoteBeat />
        </Series.Sequence>
        <Series.Sequence durationInFrames={SCENE}>
          <MontageScene
            clipName="sick_cow.mp4"
            callout="A014 — vet packet on his phone in 12 seconds"
            agent="HerdHealthWatcher"
            detail="Cow A014 · pinkeye 83%"
            accent="warn"
            anchorLabel="Vet packet"
            anchorTopic="Cow A014 · pinkeye"
            anchorHash="4d82…b03c"
            anchorStatus="Sent"
            voFile="voiceover/vo-montage-sick.mp3"
          />
        </Series.Sequence>
        <Series.Sequence durationInFrames={SCENE}>
          <MontageScene
            clipName="water.mp4"
            callout="Tank 7 dropped to 8 PSI — drone flew it before sunrise"
            agent="GrazingOptimizer"
            detail="Tank 7 · pressure drop"
            accent="sky"
            anchorLabel="IR flyover"
            anchorTopic="Tank 7"
            anchorHash="92e1…5a0d"
            anchorStatus="Queued"
            voFile="voiceover/vo-montage-tank.mp3"
          />
        </Series.Sequence>
        <Series.Sequence durationInFrames={SCENE}>
          <MontageScene
            clipName="calving.mp4"
            callout="117's calving — pinged at 3:14am"
            agent="CalvingWatch"
            detail="Cow 117 · pre-labor · priority"
            accent="sage"
            anchorLabel="Behavior trace"
            anchorTopic="Cow 117"
            anchorHash="61bf…2c94"
            anchorStatus="Paged"
            voFile="voiceover/vo-montage-calving.mp3"
          />
        </Series.Sequence>
        <Series.Sequence durationInFrames={SCENE}>
          <MontageScene
            clipName="storm.mp4"
            callout="Hail in 45min — herd routed to Shelter 2"
            agent="Weather-Redirect"
            detail="Paddock B → Shelter 2"
            accent="dust"
            anchorLabel="Redirect plan"
            anchorTopic="Paddock B → Shelter 2"
            anchorHash="d3a9…7e11"
            anchorStatus="Active"
            voFile="voiceover/vo-montage-storm.mp3"
          />
        </Series.Sequence>
        <Series.Sequence durationInFrames={MESH}>
          <MeshBeat />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};
