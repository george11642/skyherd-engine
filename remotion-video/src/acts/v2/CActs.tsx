/**
 * v5.3 — Variant C 9-scene layout (3:02 / 182s / 5460 frames @ 30fps).
 *
 * Act 1 Hook  (28s /  840f) : cold-open slam (6s) + hook VO (22s)
 * Act 2 Story (41s / 1230f) : TraditionalWay (24s) + NervousSystemStack (17s)
 * Act 3 Demo  (52s / 1560f) : live coyote dashboard (28s) + ScenarioGrid (24s)
 * Act 4 Sub   (45s / 1350f) : SoftwareMVPBlocks (23s) + VisionTimeline (22s)
 * Act 5 Close (16s /  480f) : AIBodyClose (13s) + wordmark tail (3s)
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
// v5.4 rebalanced: act5 starts at frame 4950 = 165s (act1+act2+act3+act4 = 28+40+52+45)
const C_ACT5_START = 165;

const FPS = 30;

// ── Shared helpers ────────────────────────────────────────────────────────────

// Keep AnchorChip and LowerThird imports alive (used in CoyoteDashboard below)
void (AnchorChip as unknown);
void (LowerThird as unknown);

// ── Scene 1: Cold Open (3s / 90 frames, silent) ───────────────────────────────

/**
 * "1 rancher · 10,000 acres · 0 sleep" slam.
 * v5.1: cold open is 180f total. Slam owns the first 90f, then hands off
 *  to ColdOpenAerial ($1.8B/yr). Fade in 0–18, hold, exit 75–95.
 */
const ColdOpenSlam = () => {
  const frame = useCurrentFrame();
  const opacityIn = interpolate(frame, [0, 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const opacityOut = interpolate(frame, [75, 95], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill
      style={{
        backgroundColor: "rgb(8 10 14)",
        alignItems: "center",
        justifyContent: "center",
        opacity: Math.min(opacityIn, opacityOut),
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
 * "$1.8B / yr" aerial cut — v5.1 polish: extended to 180f (6s) for plot landing.
 *  Slam owns 0–95; aerial $1.8B then takes the rest:
 *  - 80→110  fade-in
 *  - 110→160 long opacity plateau (the stat dwells ~1.7s so it registers)
 *  - 160→172 fade out
 *  - 168→180 outO crossfade tail into hook
 *  - statScale: 0.95 → 1.0 spring on entry (frames 80–100) so it lands rather than just fades
 */
const ColdOpenAerial = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const statFadeIn = interpolate(frame, [80, 110], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const statFadeOut = interpolate(frame, [160, 172], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const statO = Math.min(statFadeIn, statFadeOut);
  // Slight scale pop so the $1.8B plate "lands"
  const scaleSp = spring({
    frame: frame - 80,
    fps,
    config: { damping: 12, stiffness: 90, mass: 1 },
  });
  const statScale = interpolate(scaleSp, [0, 1], [0.95, 1.0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  // 12-frame crossfade tail into hook
  const outO = interpolate(frame, [168, 180], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill style={{ opacity: outO }}>
      <Video
        src={staticFile("clips/ambient_establish.mp4")}
        startFrom={0}
        endAt={180}
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
          transform: `scale(${statScale})`,
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

// ── Scene 2: Hook VO (22s / 660 frames) ──────────────────────────────────────
//
// VO text: "I'm George, senior at UNM. I've spent a lot of nights on New Mexico
// ranches watching ranchers do impossible work. Right now beef prices are at
// record highs — but the American cow herd is at a sixty-five-year low. Labor's
// gone. Ranchers are aging out. Every ranch left has to do more, with fewer
// people watching it."
//
// Key callout moments (approximate VO timestamps → frames):
//   "beef prices"        ~7s  → frame 210
//   "record highs"       ~8s  → frame 240
//   "sixty-five-year low"~11s → frame 330
//   "aging out"          ~15s → frame 450
//   "fewer people"       ~18s → frame 540

// Pulse callout: a number/phrase that scales in and holds for ~2s
type CalloutProps = {
  text: string;
  subtext?: string;
  appearFrame: number;
  color?: string;
  size?: number;
};

const HookCallout = ({ text, subtext, appearFrame, color = ACCENT_MAP.dust, size = 96 }: CalloutProps) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({
    frame: frame - appearFrame,
    fps,
    config: { damping: 80, stiffness: 280, mass: 0.5 },
  });
  const scale = interpolate(p, [0, 1], [0.7, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const opacity = interpolate(p, [0, 1], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  // Hold then fade out after 2.5s
  const exitO = interpolate(frame, [appearFrame + 75, appearFrame + 90], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const finalO = Math.min(opacity, exitO);

  return (
    <div
      style={{
        position: "absolute",
        top: "50%",
        left: "50%",
        transform: `translate(-50%, -50%) scale(${scale})`,
        opacity: finalO,
        textAlign: "center",
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          fontFamily: "Inter, sans-serif",
          fontWeight: 800,
          fontSize: size,
          color,
          letterSpacing: "-0.03em",
          lineHeight: 1.0,
          textShadow: "0 6px 40px rgba(0,0,0,0.8)",
        }}
      >
        {text}
      </div>
      {subtext && (
        <div
          style={{
            fontFamily: "Inter, sans-serif",
            fontWeight: 600,
            fontSize: size * 0.28,
            color: "rgb(200 210 220)",
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            marginTop: 10,
            textShadow: "0 3px 18px rgba(0,0,0,0.7)",
          }}
        >
          {subtext}
        </div>
      )}
    </div>
  );
};

const HookIntroVo = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  // v5.1 polish: 12-frame fade-in to crossfade with ColdOpenAerial outO tail
  const opacity = useFadeInOut(durationInFrames, 12, 18);
  const zoom = interpolate(frame, [0, durationInFrames], [1.0, 1.06]);

  // ID badge fades in early and stays
  const badgeO = interpolate(frame, [20, 48], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // "beef prices / record highs" callout at ~7s
  const BEEF_F = 210;
  // "65-year low" callout at ~11s
  const LOW_F = 330;
  // "aging out" callout at ~15s
  const AGING_F = 450;
  // "fewer people" callout at ~18s
  const FEWER_F = 540;

  // Active callout: only one is visible at a time — track which window we're in
  const showBeef  = frame >= BEEF_F  && frame < BEEF_F  + 90;
  const showLow   = frame >= LOW_F   && frame < LOW_F   + 90;
  const showAging = frame >= AGING_F && frame < AGING_F + 90;
  const showFewer = frame >= FEWER_F && frame < FEWER_F + 90;
  const anyCallout = showBeef || showLow || showAging || showFewer;

  // Bottom tagline: visible when no callout is active and after frame 48
  const taglineO = interpolate(frame, [48, 70], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  }) * (anyCallout ? 0 : 1);

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(8 10 14)", opacity }}>
      <Audio src={staticFile("voiceover/vo-c-hook.mp3")} />
      {/* Slow Ken-Burns aerial */}
      <div style={{ width: "100%", height: "100%", transform: `scale(${zoom})`, overflow: "hidden" }}>
        <Video
          src={staticFile("clips/ambient_establish.mp4")}
          startFrom={0}
          endAt={durationInFrames + 60}
          muted
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            filter: "saturate(0.88) contrast(1.06) brightness(0.52)",
          }}
        />
      </div>
      {/* Bottom gradient vignette */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(6,8,12,0.35) 0%, rgba(6,8,12,0) 35%, rgba(6,8,12,0) 55%, rgba(6,8,12,0.88) 100%)",
        }}
      />

      {/* Callout pulses — one at a time, centered */}
      {showBeef  && <HookCallout text="Record Highs"   subtext="Beef prices · 2026" appearFrame={BEEF_F}  color={ACCENT_MAP.dust} size={110} />}
      {showLow   && <HookCallout text="65-Year Low"    subtext="US cow herd"        appearFrame={LOW_F}   color={ACCENT_MAP.warn} size={120} />}
      {showAging && <HookCallout text="Aging Out"      subtext="Ranch labor"        appearFrame={AGING_F} color={ACCENT_MAP.thermal} size={100} />}
      {showFewer && <HookCallout text="Fewer People"   subtext="More acres to cover" appearFrame={FEWER_F} color={ACCENT_MAP.sage} size={100} />}

      {/* Bottom ID + tagline — hidden while callout is active */}
      <div
        style={{
          position: "absolute",
          bottom: 100,
          left: 90,
          right: 90,
          fontFamily: "Inter, sans-serif",
          color: "rgb(236 239 244)",
          opacity: Math.min(badgeO, taglineO > 0 ? 1 : badgeO),
        }}
      >
        <div
          style={{
            fontSize: 13,
            color: ACCENT_MAP.sage,
            letterSpacing: "0.36em",
            textTransform: "uppercase",
            fontWeight: 700,
            marginBottom: 12,
            opacity: badgeO,
          }}
        >
          George Teifel · UNM · Part 107 Certified
        </div>
        <div
          style={{
            fontSize: 44,
            fontWeight: 800,
            letterSpacing: "-0.018em",
            maxWidth: 1100,
            lineHeight: 1.08,
            color: "rgb(236 239 244)",
            textShadow: "0 4px 28px rgba(0,0,0,0.7)",
            opacity: taglineO,
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
  const COLD = C_LAYOUT.act1.coldOpenSeconds * FPS; // 6s = 180f
  const HOOK = C_LAYOUT.act1.hookSeconds * FPS;     // 22s = 660f

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
  const TRAD = C_LAYOUT.act2.traditionalSeconds * FPS; // 24s = 720f
  const ANS  = C_LAYOUT.act2.answerSeconds * FPS;      // 18s = 540f

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

// ── Scene: Live Coyote Dashboard (28s / 840 frames) ──────────────────────────

/**
 * Jargon-free live coyote FenceLineDispatcher dashboard.
 * VO is vo-c-coyote.mp3 (~22.4s); the remaining ~5.6s is the live dashboard
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

  // SMS callout appears at ~16s into the scene (was 19s — pulled 3s earlier)
  const SMS_AT = 16 * FPS;
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
        appearFrame={30}
        durationInFrames={durationInFrames - 30}
      />
      {/* Outcome chip — no jargon (was 22s → 19s) */}
      <AnchorChip
        label="Result"
        topic="Fence W-12 breach"
        hash="Drone deterred"
        statusPill="Resolved"
        appearFrame={19 * FPS}
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
  const COYOTE = C_LAYOUT.act3.coyoteSeconds * FPS; // 28s = 840f
  const GRID   = C_LAYOUT.act3.gridSeconds * FPS;   // 24s = 720f

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(8 10 14)" }}>
      <Series>
        <Series.Sequence durationInFrames={COYOTE}>
          <AbsoluteFill style={{ backgroundColor: "rgb(8 10 14)" }}>
            <CoyoteDashboard />
          </AbsoluteFill>
        </Series.Sequence>
        <Series.Sequence durationInFrames={GRID}>
          <AbsoluteFill style={{ backgroundColor: "rgb(248 244 234)" }}>
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
  const MVP    = C_LAYOUT.act4.mvpSeconds * FPS;    // 21s = 630f
  const VISION = C_LAYOUT.act4.visionSeconds * FPS; // 21s = 630f

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

// ── Wordmark tail (4s / 120 frames, silent) ───────────────────────────────────

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
  const AIBODY   = C_LAYOUT.act5.aibodySeconds * FPS;   // 12s = 360f
  const WORDMARK = C_LAYOUT.act5.wordmarkSeconds * FPS; // 4s = 120f

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
