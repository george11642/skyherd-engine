/**
 * v2 — Variants A & B Act 3 (Close, 30s).
 *
 * Phase 3 restructure: SubstanceBeat (15s) → MetaLoopBeat (5s) → FinalBeat (10s).
 *
 * - SubstanceBeat (was 18s → now 15s): dropped Fresh-clone block; tests + Ed25519 remain.
 * - MetaLoopBeat (NEW 5s): StyledCaptionsRevealer + vo-meta-{variant}.mp3.
 * - FinalBeat (was 12s → now 10s): wordmark reads in 8s; fadeout window 25→15 frames.
 *
 * B-roll is composited at z=1 by BrollTrack. SubstanceBeat uses the
 * drone-rangeland-aerial cut (150–168s in the EDL) via the shared track.
 * Act 3 starts at global second ~150 for A/B (actual offset depends on act1+act2 durations).
 */
import {
  AbsoluteFill,
  Audio,
  Series,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { BrollTrack, type BrollCut } from "../../components/BrollTrack";
import { StyledCaptionsRevealer } from "../../components/StyledCaptionsRevealer";
import { ACCENT_MAP, useFadeInOut } from "./shared";
import brollARaw from "../../data/broll-A.json";
import brollBRaw from "../../data/broll-B.json";

const BROLL_A: BrollCut[] = (brollARaw as { cuts: BrollCut[] }).cuts;
const BROLL_B: BrollCut[] = (brollBRaw as { cuts: BrollCut[] }).cuts;

// Act 3 global start in the A/B composition (seconds).
// Act1≈60s + Act2≈90s ≈ 150s offset.
const ACT3_START_SECONDS = 150;

const FPS = 30;

// Phase 3 beat durations (seconds):
const SUBSTANCE_S = 15;  // was 18; dropped Fresh-clone block
const META_LOOP_S = 5;   // NEW — Opus meta-loop reveal
const FINAL_S = 10;      // was 12; tighter fadeout window

// ── Substance beat (15s) ─────────────────────────────────────────────────────
const SubstanceBeat = () => {
  const frame = useCurrentFrame();
  const { durationInFrames, fps } = useVideoConfig();
  const opacity = useFadeInOut(durationInFrames, 22, 22);

  // Dropped "Fresh-clone reproducible" block (now in C's story arc).
  const blocks = [
    { at: 30, text: "1,106 tests · 87% coverage" },
    { at: 150, text: "Ed25519 attestation chain · 360 events" },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(8 10 14)", opacity }}>
      <Audio src={staticFile("voiceover/vo-close-substance.mp3")} />
      {/* Dark base — BrollTrack composites drone-rangeland-aerial at z=1 */}
      <AbsoluteFill style={{ backgroundColor: "rgb(6 8 12)" }} />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(90deg, rgba(6,8,12,0.85) 0%, rgba(6,8,12,0.45) 60%, rgba(6,8,12,0.45) 100%)",
        }}
      />

      <div
        style={{
          position: "absolute",
          left: 100,
          top: "30%",
          maxWidth: 900,
          fontFamily: "Inter, sans-serif",
        }}
      >
        <div
          style={{
            fontSize: 14,
            color: ACCENT_MAP.sage,
            letterSpacing: "0.34em",
            textTransform: "uppercase",
            fontWeight: 600,
            marginBottom: 28,
          }}
        >
          Substance · provable
        </div>
        {blocks.map((b, i) => {
          const p = spring({
            frame: frame - b.at,
            fps,
            config: { damping: 100, stiffness: 200, mass: 0.7 },
          });
          const x = interpolate(p, [0, 1], [40, 0]);
          const o = interpolate(p, [0, 1], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return (
            <div
              key={`block-${i}`}
              style={{
                transform: `translateX(${x}px)`,
                opacity: o,
                fontSize: 44,
                fontWeight: 700,
                color: i === 1 ? ACCENT_MAP.dust : "rgb(236 239 244)",
                letterSpacing: "-0.018em",
                marginBottom: 18,
                lineHeight: 1.15,
                textShadow: "0 6px 24px rgba(0,0,0,0.6)",
              }}
            >
              {b.text}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ── Meta-loop beat (5s, NEW) ─────────────────────────────────────────────────
type MetaLoopBeatProps = { variant: "A" | "B" };

const MetaLoopBeat = ({ variant }: MetaLoopBeatProps) => {
  return (
    <AbsoluteFill>
      <Audio src={staticFile(`voiceover/vo-meta-${variant}.mp3`)} />
      <StyledCaptionsRevealer variant={variant} appearFrame={0} />
    </AbsoluteFill>
  );
};

// ── Final wordmark beat (10s) ─────────────────────────────────────────────────
const FinalBeat = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const fadeIn = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  // Tightened: was 25 frames → 15 frames
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 15, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const opacity = Math.min(fadeIn, fadeOut);

  const wordmarkP = spring({
    frame: frame - 8,
    fps,
    config: { damping: 120, stiffness: 150, mass: 0.8 },
  });
  const wordmarkScale = interpolate(wordmarkP, [0, 1], [0.9, 1]);
  const wordmarkOpacity = interpolate(wordmarkP, [0, 1], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  // Lines still fade in at frame 50 but wordmark reads in 8s
  const linesOpacity = interpolate(frame, [50, 90], [0, 1], {
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
      <Audio src={staticFile("voiceover/vo-close-final.mp3")} />

      {/* Isometric brand placeholder — radial sage glow over warm cream */}
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse 70% 55% at 50% 50%, rgba(210,178,138,0.45) 0%, rgba(248,244,234,0) 80%)",
        }}
      />

      <div
        style={{
          transform: `scale(${wordmarkScale})`,
          opacity: wordmarkOpacity,
          fontFamily: "Inter, sans-serif",
          fontWeight: 800,
          fontSize: 200,
          color: "rgb(40 56 44)",
          letterSpacing: "-0.04em",
          lineHeight: 1,
          zIndex: 1,
        }}
      >
        Sky<span style={{ color: ACCENT_MAP.sage }}>Herd</span>
      </div>

      <div
        style={{
          marginTop: 50,
          opacity: linesOpacity,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 14,
          fontFamily: "Inter, sans-serif",
          color: "rgb(72 84 76)",
          textAlign: "center",
          zIndex: 1,
        }}
      >
        <div
          style={{
            fontSize: 28,
            color: "rgb(132 92 56)",
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
            color: "rgb(72 84 76)",
            letterSpacing: "0.02em",
          }}
        >
          MIT · Python 3.11 · TypeScript 5.8 · Opus 4.7 · 1106 tests · 87% coverage · Ed25519
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

// ── Act 3 root ───────────────────────────────────────────────────────────────

type Act3Props = { variant?: "A" | "B" };

export const ABAct3Close = ({ variant = "A" }: Act3Props) => {
  const SUBSTANCE = SUBSTANCE_S * FPS; // 450 frames
  const META_LOOP = META_LOOP_S * FPS; // 150 frames
  const FINAL = FINAL_S * FPS;         // 300 frames
  const brollTrack = variant === "B" ? BROLL_B : BROLL_A;

  return (
    <AbsoluteFill>
      {/* z=1 b-roll — drone-rangeland-aerial covers the SubstanceBeat (150–168s) */}
      <BrollTrack track={brollTrack} compositionStartSeconds={ACT3_START_SECONDS} />
      <Series>
        <Series.Sequence durationInFrames={SUBSTANCE}>
          <SubstanceBeat />
        </Series.Sequence>
        <Series.Sequence durationInFrames={META_LOOP}>
          <MetaLoopBeat variant={variant} />
        </Series.Sequence>
        <Series.Sequence durationInFrames={FINAL}>
          <FinalBeat />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};
