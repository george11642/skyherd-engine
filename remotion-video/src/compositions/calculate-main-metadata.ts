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

  // Variant C — 5-act differentiated
  hookC: "voiceover/vo-hook-C.mp3",
  storyC: "voiceover/vo-story-C.mp3",
  opusC: "voiceover/vo-opus-C.mp3",
  depthC: "voiceover/vo-depth-C.mp3",
  closeC: "voiceover/vo-close-C.mp3",
} as const;

export type VoKey = keyof typeof VO_FILES;

/**
 * Fallback durations (seconds) keyed by VO beat. Measured 2026-04-24 from
 * iter2 Will/eleven_v3 renders. Used when public/ MP3 files cannot be measured
 * at metadata-resolution time (e.g. CI without public/).
 */
const FALLBACK_VO_SECONDS: Record<VoKey, number> = {
  // Shared deep scenario
  coyoteDeep: 28.53,

  // Shared (A/B)
  market: 17.95,
  compare: 30.85,
  meshOpus: 30.43,
  closeSubstance: 16.93,
  closeFinal: 7.24,

  // Variant A
  intro: 13.64,

  // Variant B
  introB: 19.88,

  // Variant C
  hookC: 14.45,
  storyC: 42.68,
  opusC: 30.85,
  depthC: 17.63,
  closeC: 9.17,
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
const AB_ACT1_MARKET_MIN_SECONDS = 20;
const AB_ACT1_COMPARE_MIN_SECONDS = 18;

// A & B — Act 2 (~90s) — iter2: one deep scenario + rapid montage + mesh
//   0–25   deep coyote scenario (25 s)
//   25–50  4-scenario montage (~6 s each, ~25 s total, no full VO)
//   50–90  mesh + Opus 4.7 reveal (40 s)
const AB_ACT2_COYOTE_DEEP_MIN_SECONDS = 25;
const AB_ACT2_MONTAGE_SECONDS = 25;
const AB_ACT2_MONTAGE_SCENE_COUNT = 4;
const AB_ACT2_MESH_MIN_SECONDS = 40;

// A & B — Act 3 (~30s)
const AB_ACT3_SUBSTANCE_SECONDS = 18;
const AB_ACT3_FINAL_SECONDS = 12;

// C — Act 1 (Hook, ~20s)
const C_ACT1_HOOK_PUNCH_SECONDS = 8;
const C_ACT1_HOOK_VO_MIN_SECONDS = 12;

// C — Act 2 (Story + compare, ~40s — compare fused into story in iter2)
const C_ACT2_STORY_MIN_SECONDS = 38;

// C — Act 3 (Demo, ~55s) — deep coyote + montage + short synthesis
const C_ACT3_COYOTE_DEEP_MIN_SECONDS = 25;
const C_ACT3_MONTAGE_SECONDS = 25;
const C_ACT3_MONTAGE_SCENE_COUNT = 4;
const C_ACT3_SYNTHESIS_SECONDS = 5;

// C — Act 4 (Substance, ~45s in iter2) — Opus (~25s) + Depth (~20s)
const C_ACT4_OPUS_MIN_SECONDS = 25;
const C_ACT4_DEPTH_MIN_SECONDS = 20;

// C — Act 5 (Close, ~20s)
const C_ACT5_BOOKEND_SECONDS = 13;
const C_ACT5_WORDMARK_SECONDS = 7;

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
    finalSeconds: AB_ACT3_FINAL_SECONDS,
  },
} as const;

export const C_LAYOUT = {
  act1: {
    punchSeconds: C_ACT1_HOOK_PUNCH_SECONDS,
    voMin: C_ACT1_HOOK_VO_MIN_SECONDS,
  },
  act2: { storyMin: C_ACT2_STORY_MIN_SECONDS },
  act3: {
    coyoteDeepMin: C_ACT3_COYOTE_DEEP_MIN_SECONDS,
    montageSeconds: C_ACT3_MONTAGE_SECONDS,
    montageSceneCount: C_ACT3_MONTAGE_SCENE_COUNT,
    synthesisSeconds: C_ACT3_SYNTHESIS_SECONDS,
  },
  act4: {
    opusMin: C_ACT4_OPUS_MIN_SECONDS,
    depthMin: C_ACT4_DEPTH_MIN_SECONDS,
  },
  act5: {
    bookendSeconds: C_ACT5_BOOKEND_SECONDS,
    wordmarkSeconds: C_ACT5_WORDMARK_SECONDS,
  },
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
    // C — 5-act layout, iter2: Hook (~20s) / Story+compare (~45s) / Demo
    // deep+montage+synth (~55s) / Substance Opus+Depth (~45-50s) / Close (~20s)
    const act1Seconds = Math.max(
      C_ACT1_HOOK_PUNCH_SECONDS +
        Math.max(voSeconds.hookC + 0.5, C_ACT1_HOOK_VO_MIN_SECONDS),
      20,
    );
    const act2Seconds = Math.max(voSeconds.storyC + 2, 40);
    const act3Seconds =
      Math.max(voSeconds.coyoteDeep + 1, C_ACT3_COYOTE_DEEP_MIN_SECONDS) +
      C_ACT3_MONTAGE_SECONDS +
      C_ACT3_SYNTHESIS_SECONDS;
    const act4Seconds =
      Math.max(voSeconds.opusC + 1, C_ACT4_OPUS_MIN_SECONDS) +
      Math.max(voSeconds.depthC + 1, C_ACT4_DEPTH_MIN_SECONDS);
    const act5Seconds = C_ACT5_BOOKEND_SECONDS + C_ACT5_WORDMARK_SECONDS;

    actDurations = {
      act1: framesFromSeconds(act1Seconds),
      act2: framesFromSeconds(act2Seconds),
      act3: framesFromSeconds(act3Seconds),
      act4: framesFromSeconds(act4Seconds),
      act5: framesFromSeconds(act5Seconds),
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
    const act3Seconds = AB_ACT3_SUBSTANCE_SECONDS + AB_ACT3_FINAL_SECONDS;

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
