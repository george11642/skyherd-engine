/**
 * v4 — Variant C 9-scene layout (3:00 / 180s / 5400 frames @ 30fps).
 *
 * Act 1 Hook  (18s / 540f)  : cold-open slam (3s) + hook VO (15s)
 * Act 2 Story (34s / 1020f) : TraditionalWay (17s) + NervousSystemStack (17s)
 * Act 3 Demo  (58s / 1740f) : live coyote dashboard (40s) + ScenarioGrid (18s)
 * Act 4 Sub   (42s / 1260f) : SoftwareMVPBlocks (20s) + VisionTimeline (22s)
 * Act 5 Close (28s / 840f)  : AIBodyClose (23s) + wordmark tail (5s)
 *
 * Each scene's animations are relative to its Series.Sequence mount frame.
 * VO Audio tags fire at scene-relative frame 0.
 *
 * Removed in v4:
 *   - StyledCaptionsRevealer (import + usage)
 *   - COpusBeat, CDepthBeat, CSynthesisBeat, CMontageScene, CDeepCoyote
 *   - "attestation", "Merkle", "Ed25519", "ledger", "signed.*byte" strings
 *   - old VO references (vo-hook-C, vo-story-C, vo-coyote-deep, vo-opus-C,
 *     vo-depth-C, vo-close-C, vo-montage-*)
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
import { C_LAYOUT } from "../../compositions/calculate-main-metadata";
import { BrollTrack, type BrollCut } from "../../components/BrollTrack";
import {
  ACCENT_MAP,
  type Accent,
  AnchorChip,
  KineticPunch,
  LowerThird,
  useFadeInOut,
} from "./shared";
import { TraditionalWay } from "../../components/diagrams/TraditionalWay";
import { NervousSystemStack } from "../../components/diagrams/NervousSystemStack";
import { ScenarioGrid } from "../../components/diagrams/ScenarioGrid";
import { SoftwareMVPBlocks } from "../../components/diagrams/SoftwareMVPBlocks";
import { VisionTimeline } from "../../components/diagrams/VisionTimeline";
import { AIBodyClose } from "../../components/diagrams/AIBodyClose";
import brollCRaw from "../../data/broll-C.json";

const BROLL_C: BrollCut[] = (brollCRaw as { cuts: BrollCut[] }).cuts;

// Global act offsets (seconds) used by BrollTrack
const C_ACT5_START = 160;

const FPS = 30;

// ── Shared helpers ────────────────────────────────────────────────────────────

// Keep AnchorChip and LowerThird imports alive (used in CoyoteDashboard below)
void (AnchorChip as unknown);
void (LowerThird as unknown);

// ── Scene 1: Cold Open (3s / 90 frames, silent) ───────────────────────────────

/**
 * "1 rancher · 10,000 acres · 0 sleep" slam.
 * Holds from frame 0, exits at f75→90 to avoid bleeding into hook VO.
 */
const ColdOpenSlam = () => {
  const frame = useCurrentFrame();
  const opacityOut = interpolate(frame, [60, 90], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill
      style={{
        backgroundColor: "rgb(8 10 14)",
        alignItems: "center",
        justifyContent: "center",
        opacity: opacityOut,
      }}
    >
      <div
        style={{
          fontFamily: "Inter, sans-serif",
          fontWeight: 800,
          fontSize: 96,
          color: "rgb(236 239 244)",
          letterSpacing: "-0.025em",
          textAlign: "center",
          lineHeight: 1.06,
          textShadow: "0 6px 28px rgba(0,0,0,0.7)",
        }}
      >
        1 rancher
        <br />
        10,000 acres
        <br />
        <span style={{ color: ACCENT_MAP.warn }}>0 sleep</span>
      </div>
    </AbsoluteFill>
  );
};

/**
 * "$1.8B / yr" aerial cut — appears at f8, exits at end of cold open.
 */
const ColdOpenAerial = () => {
  const frame = useCurrentFrame();
  const statO = interpolate(frame, [8, 26], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill>
      <Video
        src={staticFile("clips/ambient_establish.mp4")}
        startFrom={0}
        endAt={90}
        muted
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          filter: "saturate(0.85) contrast(1.05) brightness(0.55)",
        }}
      />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(6,8,12,0.45) 0%, rgba(6,8,12,0.78) 100%)",
        }}
      />
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          padding: "0 8%",
          opacity: statO,
          flexDirection: "column",
          gap: 18,
        }}
      >
        <div
          style={{
            fontFamily: "Inter, sans-serif",
            fontWeight: 600,
            fontSize: 22,
            color: ACCENT_MAP.sage,
            letterSpacing: "0.32em",
            textTransform: "uppercase",
          }}
        >
          US ranchers · annual loss
        </div>
        <div
          style={{
            fontFamily: "Inter, sans-serif",
            fontWeight: 800,
            fontSize: 160,
            color: ACCENT_MAP.dust,
            letterSpacing: "-0.03em",
            lineHeight: 1.0,
            textAlign: "center",
            textShadow: "0 8px 36px rgba(0,0,0,0.7)",
          }}
        >
          $1.8B / yr
        </div>
        <div
          style={{
            fontFamily: "Inter, sans-serif",
            fontWeight: 700,
            fontSize: 32,
            color: "rgb(236 239 244)",
            letterSpacing: "0.04em",
            textAlign: "center",
            textShadow: "0 4px 22px rgba(0,0,0,0.7)",
          }}
        >
          predators &amp; strays
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ── Scene 2: Hook + Intro VO (15s / 450 frames) ───────────────────────────────

const HookIntroVo = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const opacity = useFadeInOut(durationInFrames, 18, 18);
  const zoom = interpolate(frame, [0, durationInFrames], [1.0, 1.08]);

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(8 10 14)", opacity }}>
      <Audio src={staticFile("voiceover/vo-c-hook.mp3")} />
      <div
        style={{
          width: "100%",
          height: "100%",
          transform: `scale(${zoom})`,
        }}
      >
        <Video
          src={staticFile("clips/ambient_establish.mp4")}
          startFrom={0}
          endAt={durationInFrames + 60}
          muted
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            filter: "saturate(0.92) contrast(1.04)",
          }}
        />
      </div>
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(10,12,16,0) 50%, rgba(10,12,16,0.85) 100%)",
        }}
      />
      {/* Kinetic typography: key phrases appear over the VO */}
      <KineticPunch
        words={[
          {
            text: "$4.17",
            appearFrame: 30,
            fastFade: 6,
            scaleFrom: 1.4,
            weight: 800,
            size: 200,
            color: ACCENT_MAP.dust,
          },
          {
            text: "/ week",
            appearFrame: 60,
            weight: 500,
            size: 48,
            color: "rgb(60 72 56)",
          },
          {
            text: "24 / 7",
            appearFrame: 120,
            weight: 800,
            size: 88,
            color: ACCENT_MAP.sage,
          },
          {
            text: "nervous system",
            appearFrame: 160,
            weight: 800,
            size: 60,
            color: ACCENT_MAP.sage,
          },
          {
            text: "10,000-acre ranch",
            appearFrame: 200,
            weight: 600,
            size: 42,
            color: "rgb(60 72 56)",
          },
        ]}
      />
      <div
        style={{
          position: "absolute",
          bottom: 110,
          left: 90,
          fontFamily: "Inter, sans-serif",
          color: "rgb(236 239 244)",
          opacity: interpolate(frame, [25, 55], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        <div
          style={{
            fontSize: 14,
            color: ACCENT_MAP.sage,
            letterSpacing: "0.34em",
            textTransform: "uppercase",
            fontWeight: 600,
            marginBottom: 10,
          }}
        >
          George Teifel · UNM · Part 107
        </div>
        <div
          style={{
            fontSize: 38,
            fontWeight: 700,
            letterSpacing: "-0.012em",
            maxWidth: 1200,
            lineHeight: 1.1,
          }}
        >
          Every fence. Every trough. Every cow.
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── Act 1 Export ──────────────────────────────────────────────────────────────

export const CAct1Hook = () => {
  const COLD = C_LAYOUT.act1.coldOpenSeconds * FPS; // 3s = 90f
  const HOOK = C_LAYOUT.act1.hookSeconds * FPS;     // 15s = 450f

  return (
    <AbsoluteFill>
      <Series>
        <Series.Sequence durationInFrames={COLD}>
          <AbsoluteFill>
            <ColdOpenAerial />
            <ColdOpenSlam />
          </AbsoluteFill>
        </Series.Sequence>
        <Series.Sequence durationInFrames={HOOK}>
          <HookIntroVo />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};

// ── Act 2 Export ──────────────────────────────────────────────────────────────

export const CAct2Story = () => {
  const TRAD = C_LAYOUT.act2.traditionalSeconds * FPS; // 17s = 510f
  const ANS  = C_LAYOUT.act2.answerSeconds * FPS;      // 17s = 510f

  return (
    <AbsoluteFill>
      <Series>
        <Series.Sequence durationInFrames={TRAD}>
          <AbsoluteFill>
            <Audio src={staticFile("voiceover/vo-c-traditional.mp3")} />
            <TraditionalWay />
          </AbsoluteFill>
        </Series.Sequence>
        <Series.Sequence durationInFrames={ANS}>
          <AbsoluteFill>
            <Audio src={staticFile("voiceover/vo-c-answer.mp3")} />
            <NervousSystemStack />
          </AbsoluteFill>
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};

// ── Scene: Live Coyote Dashboard (40s / 1200 frames) ─────────────────────────

/**
 * Jargon-free live coyote FenceLineDispatcher dashboard.
 * VO is vo-c-coyote.mp3 (~16.4s); the remaining ~24s is the live dashboard
 * continuing to play through the scenario.
 */
const CoyoteDashboard = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const fadeIn = interpolate(frame, [0, 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 15, durationInFrames],
    [1, 0.25],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const opacity = Math.min(fadeIn, fadeOut);

  // SMS callout appears at ~19s into the scene
  const SMS_AT = 19 * FPS;
  const smsO = interpolate(frame, [SMS_AT, SMS_AT + 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(6 8 12)" }}>
      <Audio src={staticFile("voiceover/vo-c-coyote.mp3")} />
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
      {/* Time badge */}
      <div
        style={{
          position: "absolute",
          top: 80,
          left: 80,
          display: "flex",
          alignItems: "center",
          gap: 14,
          opacity: fadeIn,
        }}
      >
        <div
          style={{
            width: 48,
            height: 48,
            borderRadius: 24,
            backgroundColor: ACCENT_MAP.thermal,
            color: "rgb(10 12 16)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: "Inter, sans-serif",
            fontWeight: 800,
            fontSize: 18,
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
          South fence · thermal alert
        </div>
      </div>
      {/* Agent + result callout */}
      <LowerThird
        agent="FenceLineDispatcher"
        detail="Coyote · 91% · Mavic dispatched"
        accent={"thermal" as Accent}
        appearFrame={45}
        durationInFrames={durationInFrames - 45}
      />
      {/* Outcome chip — no jargon */}
      <AnchorChip
        label="Result"
        topic="Fence W-12 breach"
        hash="Drone deterred"
        statusPill="Resolved"
        appearFrame={22 * FPS}
        accent={"thermal" as Accent}
      />
      {/* SMS card */}
      <div
        style={{
          position: "absolute",
          bottom: 220,
          right: 80,
          opacity: smsO,
          maxWidth: 400,
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
        <div style={{ fontSize: 15, lineHeight: 1.35, fontWeight: 500 }}>
          Coyote on W-12. Drone scared it off. Fence intact. You&rsquo;re good.
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── Act 3 Export ──────────────────────────────────────────────────────────────

export const CAct3Demo = () => {
  const COYOTE = C_LAYOUT.act3.coyoteSeconds * FPS; // 40s = 1200f
  const GRID   = C_LAYOUT.act3.gridSeconds * FPS;   // 18s = 540f

  return (
    <AbsoluteFill>
      <Series>
        <Series.Sequence durationInFrames={COYOTE}>
          <CoyoteDashboard />
        </Series.Sequence>
        <Series.Sequence durationInFrames={GRID}>
          <AbsoluteFill>
            <Audio src={staticFile("voiceover/vo-c-grid.mp3")} />
            <ScenarioGrid />
          </AbsoluteFill>
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};

// ── Act 4 Export ──────────────────────────────────────────────────────────────

export const CAct4Substance = () => {
  const MVP    = C_LAYOUT.act4.mvpSeconds * FPS;    // 20s = 600f
  const VISION = C_LAYOUT.act4.visionSeconds * FPS; // 22s = 660f

  return (
    <AbsoluteFill>
      <Series>
        <Series.Sequence durationInFrames={MVP}>
          <AbsoluteFill>
            <Audio src={staticFile("voiceover/vo-c-mvp.mp3")} />
            <SoftwareMVPBlocks />
          </AbsoluteFill>
        </Series.Sequence>
        <Series.Sequence durationInFrames={VISION}>
          <AbsoluteFill>
            <Audio src={staticFile("voiceover/vo-c-vision.mp3")} />
            <VisionTimeline />
          </AbsoluteFill>
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};

// ── Wordmark tail (5s / 150 frames, silent) ───────────────────────────────────

const CCloseWordmark = () => {
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
    frame: frame - 8,
    fps,
    config: { damping: 120, stiffness: 150, mass: 0.8 },
  });
  const scale = interpolate(wordmarkP, [0, 1], [0.9, 1]);
  const wo = interpolate(wordmarkP, [0, 1], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const linesO = interpolate(frame, [50, 90], [0, 1], {
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
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse 70% 55% at 50% 50%, rgba(210,178,138,0.45) 0%, rgba(248,244,234,0) 80%)",
        }}
      />
      <div
        style={{
          transform: `scale(${scale})`,
          opacity: wo,
          fontFamily: "Inter, sans-serif",
          fontWeight: 800,
          fontSize: 200,
          color: "rgb(40 56 44)",
          letterSpacing: "-0.04em",
          lineHeight: 1,
        }}
      >
        Sky<span style={{ color: ACCENT_MAP.sage }}>Herd</span>
      </div>
      <div
        style={{
          marginTop: 50,
          opacity: linesO,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 14,
          fontFamily: "Inter, sans-serif",
          color: "rgb(72 84 76)",
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontSize: 28,
            color: ACCENT_MAP.dust,
            fontWeight: 700,
            letterSpacing: "0.02em",
          }}
        >
          Built with Opus 4.7
        </div>
        <div
          style={{
            fontSize: 24,
            color: "rgb(132 92 56)",
            fontWeight: 600,
            letterSpacing: "0.02em",
          }}
        >
          github.com/george11642/skyherd-engine
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

// ── Act 5 Export ──────────────────────────────────────────────────────────────

export const CAct5Close = () => {
  const AIBODY   = C_LAYOUT.act5.aibodySeconds * FPS;   // 23s = 690f
  const WORDMARK = C_LAYOUT.act5.wordmarkSeconds * FPS; // 5s = 150f

  return (
    <AbsoluteFill>
      {/* Night-sky b-roll composited at z=1 under the close */}
      <BrollTrack track={BROLL_C} compositionStartSeconds={C_ACT5_START} />
      <Series>
        <Series.Sequence durationInFrames={AIBODY}>
          <AbsoluteFill>
            <Audio src={staticFile("voiceover/vo-c-aibody.mp3")} />
            <AIBodyClose />
          </AbsoluteFill>
        </Series.Sequence>
        <Series.Sequence durationInFrames={WORDMARK}>
          <CCloseWordmark />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};
