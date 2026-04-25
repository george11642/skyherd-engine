import { CalculateMetadataFunction, staticFile } from "remotion";
// getAudioDurationInSeconds is the current, functional API in Remotion 4.x.
// The deprecation warning in media-utils is premature; keep using it.
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore -- deprecated warning is spurious for 4.0.451
import { getAudioDurationInSeconds } from "@remotion/media-utils";

export const FPS = 30;
export const WIDTH = 1920;
export const HEIGHT = 1080;

/**
 * v2 demo cut — variant render track — Phase H iter2 humanized restructure.
 *
 * Three variants render against the same iter2 VO bus + same B-roll inventory
 * but with different act layouts and hook styles.
 *
 * - "A" (default) — winner-pattern · 3-act Setup/Demo/Close · contrarian hook ·
 *   deep coyote + 4-montage · traditional-vs-SkyHerd compare beat · emphasis
 *   captions
 * - "B" — hybrid · 3-act · metric-first hook · same demo structure as A
 * - "C" — differentiated · 5-act Hook/Story/Demo/Substance/Close · metric hook ·
 *   word-level captions
 *
 * Voice (iter2): Will — ElevenLabs voice ID bIHbv24MWmeRgasZH58o (modern
 * conversational male). Model eleven_v3 (fallback eleven_turbo_v2_5). Swapped
 * off Antoni because Antoni read as a narrator.
 *
 * Cue bus retired from iter1: vo-coyote, vo-sick-cow, vo-calving, vo-storm
 * (replaced by single vo-coyote-deep + silent montage); vo-bridge, vo-bridge-B
 * (replaced by vo-compare); vo-mesh (replaced by vo-mesh-opus that names
 * Opus 4.7 explicitly); vo-synthesis-C (silent in iter2 — music carries).
 */
export type Variant = "A" | "B" | "C";

/**
 * Voiceover files, keyed by logical beat. Each maps to a file in
 * public/voiceover/vo-*.mp3.
 */
export const VO_FILES = {
  // Shared (A, B, C — iter2 single deep scenario)
  coyoteDeep: "voiceover/vo-coyote-deep.mp3",

  // Shared (A, B — same scripts, different hooks)
  market: "voiceover/vo-market.mp3",
  compare: "voiceover/vo-compare.mp3",
  meshOpus: "voiceover/vo-mesh-opus.mp3",
  closeSubstance: "voiceover/vo-close-substance.mp3",
  closeFinal: "voiceover/vo-close-final.mp3",

  // Variant A — contrarian hook
  intro: "voiceover/vo-intro.mp3",

  // Variant B — metric-first hook
  introB: "voiceover/vo-intro-B.mp3",

  // Variant C — 5-act differentiated (v3, kept for A/B compat)
  hookC: "voiceover/vo-hook-C.mp3",
  storyC: "voiceover/vo-story-C.mp3",
  opusC: "voiceover/vo-opus-C.mp3",
  depthC: "voiceover/vo-depth-C.mp3",
  closeC: "voiceover/vo-close-C.mp3",

  // Variant C v4 — 9-scene rewrite (Wave 2C)
  cHook: "voiceover/vo-c-hook.mp3",
  cTraditional: "voiceover/vo-c-traditional.mp3",
  cAnswer: "voiceover/vo-c-answer.mp3",
  cCoyote: "voiceover/vo-c-coyote.mp3",
  cGrid: "voiceover/vo-c-grid.mp3",
  cMvp: "voiceover/vo-c-mvp.mp3",
  cVision: "voiceover/vo-c-vision.mp3",
  cAibody: "voiceover/vo-c-aibody.mp3",

  // Montage cues (Phase 2 — fills 1:25-1:50 previously-silent montage window)
  montageSick: "voiceover/vo-montage-sick.mp3",
  montageTank: "voiceover/vo-montage-tank.mp3",
  montageCalving: "voiceover/vo-montage-calving.mp3",
  montageStorm: "voiceover/vo-montage-storm.mp3",
  montageBridge: "voiceover/vo-montage-bridge.mp3",

  // Meta-loop cues (Phase 3 — ABAct3Close MetaLoopBeat)
  metaA: "voiceover/vo-meta-A.mp3",
  metaB: "voiceover/vo-meta-B.mp3",
} as const;

export type VoKey = keyof typeof VO_FILES;

/**
 * Fallback durations (seconds) keyed by VO beat. Measured 2026-04-24 from
 * iter2 Will/eleven_v3 renders. Used when public/ MP3 files cannot be measured
 * at metadata-resolution time (e.g. CI without public/).
 */
const FALLBACK_VO_SECONDS: Record<VoKey, number> = {
  // Shared deep scenario — Inworld/Nate measured 2026-04-24
  coyoteDeep: 23.09,

  // Shared (A/B)
  market: 15.70,
  compare: 24.82,
  meshOpus: 25.29,
  closeSubstance: 14.21,
  closeFinal: 6.03,

  // Variant A
  intro: 14.52,

  // Variant B
  introB: 18.68,

  // Variant C
  hookC: 12.96,
  storyC: 31.63,
  opusC: 27.72,
  depthC: 12.28,
  closeC: 7.94,

  // Montage cues (Phase 2 — measured 2026-04-24 Inworld/Nate)
  montageSick: 7.92,
  montageTank: 6.09,
  montageCalving: 6.27,
  montageStorm: 5.46,
  montageBridge: 5.07,

  // Meta-loop cues (Phase 3)
  metaA: 9.80,
  metaB: 8.07,

  // Variant C v5 — Chatterbox-cloned George voice (measured 2026-04-25 ffprobe)
  cHook: 19.152,
  cTraditional: 13.200,
  cAnswer: 15.672,
  cCoyote: 22.440,
  cGrid: 18.240,
  cMvp: 17.304,
  cVision: 12.552,
  cAibody: 11.064,
};

export type VoDurationsFrames = Record<VoKey, number>;

/**
 * Act-level durations in frames. Variant A and B use 3 acts; Variant C uses 5.
 * For uniformity all variants populate all 5 keys; A/B leave act4/act5 = 0.
 */
export type ActDurations = {
  act1: number;
  act2: number;
  act3: number;
  act4: number;
  act5: number;
};

export type MainProps = {
  variant: Variant;
  actDurations: ActDurations;
  voDurationsFrames: VoDurationsFrames;
};

const framesFromSeconds = (seconds: number): number =>
  Math.max(1, Math.ceil(seconds * FPS));

async function measureVo(
  file: string,
  fallbackSeconds: number,
): Promise<number> {
  try {
    const seconds = await getAudioDurationInSeconds(staticFile(file));
    if (!seconds || Number.isNaN(seconds)) {
      return fallbackSeconds;
    }
    return seconds;
  } catch {
    return fallbackSeconds;
  }
}

// ─── Layout constants per variant (iter2 restructure) ────────────────────────
//
// Variant A & B share a 3-act skeleton. Variant C uses a 5-act layout.
// All three land on ~180 s with the new humanized VO bus.

// A & B — Act 1 (~60s):
//   0–8   cold-open hook (8 s, no VO)
//   8–22  intro VO (~14 s)
//   22–42 market VO (~20 s)
//   42–60 traditional-vs-SkyHerd compare beat (~18 s)
const AB_ACT1_HOOK_SECONDS = 8;
const AB_ACT1_INTRO_MIN_SECONDS = 14;
const AB_ACT1_MARKET_MIN_SECONDS = 17; // Phase 3: trim MarketBeat 28s→25s (−3s from prior ~20s floor)
const AB_ACT1_COMPARE_MIN_SECONDS = 18;

// A & B — Act 2 (~90s) — iter2: one deep scenario + rapid montage + mesh
//   0–25   deep coyote scenario (25 s)
//   25–50  4-scenario montage (~6 s each, ~25 s total, no full VO)
//   50–90  mesh + Opus 4.7 reveal (40 s)
const AB_ACT2_COYOTE_DEEP_MIN_SECONDS = 25;
const AB_ACT2_MONTAGE_SECONDS = 25;
const AB_ACT2_MONTAGE_SCENE_COUNT = 4;
const AB_ACT2_MESH_MIN_SECONDS = 40;

// A & B — Act 3 (~30s) — Phase 3 restructure: 15s + 5s meta-loop + 10s = 30s
const AB_ACT3_SUBSTANCE_SECONDS = 15;
const AB_ACT3_META_LOOP_SECONDS = 5;
const AB_ACT3_FINAL_SECONDS = 10;

// C v5 — 9-scene layout mapped to 5 acts (Wave 2E, total = 180s = 5400 frames)
//
// act1 = coldOpen(3s) + hook(22s)             = 25s = 750 frames
// act2 = traditional(16s) + answer(16s)       = 32s = 960 frames
// act3 = coyote(32s) + grid(25s)              = 57s = 1710 frames
// act4 = mvp(22s) + vision(22s)               = 44s = 1320 frames
// act5 = aibody(18s) + wordmark(4s)           = 22s = 660 frames
// TOTAL                                       = 180s = 5400 frames ✓
const C_ACT1_SECONDS = 25;  // coldOpen(3) + hook(22)
const C_ACT2_SECONDS = 32;  // traditional(16) + answer(16)
const C_ACT3_SECONDS = 57;  // coyote(32) + grid(25)
const C_ACT4_SECONDS = 44;  // mvp(22) + vision(22)
const C_ACT5_SECONDS = 22;  // aibody(18) + wordmark(4)

// Re-exported for act components.
export const AB_LAYOUT = {
  act1: {
    hook: AB_ACT1_HOOK_SECONDS,
    introMin: AB_ACT1_INTRO_MIN_SECONDS,
    marketMin: AB_ACT1_MARKET_MIN_SECONDS,
    compareMin: AB_ACT1_COMPARE_MIN_SECONDS,
  },
  act2: {
    coyoteDeepMin: AB_ACT2_COYOTE_DEEP_MIN_SECONDS,
    montageSeconds: AB_ACT2_MONTAGE_SECONDS,
    montageSceneCount: AB_ACT2_MONTAGE_SCENE_COUNT,
    meshMin: AB_ACT2_MESH_MIN_SECONDS,
  },
  act3: {
    substanceSeconds: AB_ACT3_SUBSTANCE_SECONDS,
    metaLoopSeconds: AB_ACT3_META_LOOP_SECONDS,
    finalSeconds: AB_ACT3_FINAL_SECONDS,
  },
} as const;

// Re-exported for act components.
export const C_LAYOUT = {
  // act1: coldOpen(3s) + hook(22s) = 25s  [Wave 2E: hook expanded to absorb VO overflow]
  act1: { totalSeconds: C_ACT1_SECONDS, coldOpenSeconds: 3, hookSeconds: 22, punchSeconds: 3 },
  // act2: traditional(16s) + answer(16s) = 32s  [Wave 2E: -1s each for budget]
  act2: { totalSeconds: C_ACT2_SECONDS, traditionalSeconds: 16, answerSeconds: 16, storyMin: 32 },
  // act3: coyote live demo(32s) + grid(25s) = 57s  [Wave 2E: coyote -8s, grid +7s]
  act3: {
    totalSeconds: C_ACT3_SECONDS,
    coyoteSeconds: 32,
    gridSeconds: 25,
    coyoteDeepMin: 32,
    montageSeconds: 25,
    montageSceneCount: 4,
    synthesisSeconds: 0,
  },
  // act4: mvp(22s) + vision(22s) = 44s  [Wave 2E: mvp +2s]
  act4: { totalSeconds: C_ACT4_SECONDS, mvpSeconds: 22, visionSeconds: 22, opusMin: 22, depthMin: 22 },
  // act5: aibody(18s) + wordmark(4s) = 22s  [Wave 2E: aibody -5s, wordmark -1s]
  act5: { totalSeconds: C_ACT5_SECONDS, aibodySeconds: 18, wordmarkSeconds: 4, bookendSeconds: 18 },
} as const;

export const calculateMainMetadata: CalculateMetadataFunction<
  MainProps
> = async ({ props }) => {
  const variant: Variant = props.variant ?? "A";

  const keys = Object.keys(VO_FILES) as VoKey[];
  const secondsPerKey = await Promise.all(
    keys.map((k) => measureVo(VO_FILES[k], FALLBACK_VO_SECONDS[k])),
  );

  const voSeconds: Record<VoKey, number> = {} as Record<VoKey, number>;
  const voDurationsFrames: VoDurationsFrames = {} as VoDurationsFrames;
  keys.forEach((k, i) => {
    voSeconds[k] = secondsPerKey[i];
    voDurationsFrames[k] = framesFromSeconds(secondsPerKey[i]);
  });

  let actDurations: ActDurations;

  if (variant === "C") {
    // C v5 — fixed 5-act layout (Wave 2E). Scene durations redistributed to
    // absorb VO overflow from new Will/eleven_v3 recordings.
    // Total = 25+32+57+44+22 = 180s = 5400 frames.
    actDurations = {
      act1: framesFromSeconds(C_ACT1_SECONDS),
      act2: framesFromSeconds(C_ACT2_SECONDS),
      act3: framesFromSeconds(C_ACT3_SECONDS),
      act4: framesFromSeconds(C_ACT4_SECONDS),
      act5: framesFromSeconds(C_ACT5_SECONDS),
    };
  } else {
    // A & B — 3-act, iter2: Setup (~60-70s) / Demo deep+montage+mesh-opus
    // (~95-100s) / Close (~30s). Act durations stretch with the longer
    // humanized VO but calculateMetadata absorbs it via Math.max.
    const introSeconds =
      variant === "B" ? voSeconds.introB : voSeconds.intro;

    const act1Seconds = Math.max(
      AB_ACT1_HOOK_SECONDS +
        Math.max(introSeconds + 0.5, AB_ACT1_INTRO_MIN_SECONDS) +
        Math.max(voSeconds.market + 1, AB_ACT1_MARKET_MIN_SECONDS) +
        Math.max(voSeconds.compare + 1, AB_ACT1_COMPARE_MIN_SECONDS),
      60,
    );
    const act2Seconds =
      Math.max(voSeconds.coyoteDeep + 1, AB_ACT2_COYOTE_DEEP_MIN_SECONDS) +
      AB_ACT2_MONTAGE_SECONDS +
      Math.max(voSeconds.meshOpus + 1, AB_ACT2_MESH_MIN_SECONDS);
    const act3Seconds = AB_ACT3_SUBSTANCE_SECONDS + AB_ACT3_META_LOOP_SECONDS + AB_ACT3_FINAL_SECONDS;

    actDurations = {
      act1: framesFromSeconds(act1Seconds),
      act2: framesFromSeconds(act2Seconds),
      act3: framesFromSeconds(act3Seconds),
      act4: 0,
      act5: 0,
    };
  }

  const total =
    actDurations.act1 +
    actDurations.act2 +
    actDurations.act3 +
    actDurations.act4 +
    actDurations.act5;

  return {
    durationInFrames: total,
    props: {
      ...props,
      variant,
      actDurations,
      voDurationsFrames,
    },
  };
};
