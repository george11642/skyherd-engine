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
 * v2 demo cut — variant render track.
 *
 * Three variants render against the same VO bus + same B-roll inventory but
 * with different act layouts and hook styles. Phase H's dual-vision iteration
 * loop picks the winner.
 *
 * - "A" (default) — winner-pattern · 3-act Setup/Demo/Close (60/90/30 s) ·
 *   identity/contrarian hook · emphasis-only captions
 * - "B" — hybrid · 3-act same skeleton · metric-first hook · emphasis-only
 * - "C" — differentiated · 5-act Hook/Story/Demo/Substance/Close (20/50/55/35/20 s) ·
 *   metric hook · word-level kinetic captions throughout
 *
 * Voice: Antoni — ElevenLabs voice ID ErXwobaYiN019PkySvjV (neutral 19yo male,
 * college-student-engineer tone). Wes cowboy persona retired.
 */
export type Variant = "A" | "B" | "C";

/**
 * Voiceover files, keyed by logical beat. Each maps to a file in
 * public/voiceover/vo-*.mp3.
 *
 * Cues are shared across variants where text matches; A/B/C-specific cues
 * are suffixed.
 */
export const VO_FILES = {
  // Shared scenario cues (used by A, B, C)
  coyote: "voiceover/vo-coyote.mp3",
  sickCow: "voiceover/vo-sick-cow.mp3",
  calving: "voiceover/vo-calving.mp3",
  storm: "voiceover/vo-storm.mp3",

  // Shared market + close cues (used by A and B; C has its own)
  market: "voiceover/vo-market.mp3",
  mesh: "voiceover/vo-mesh.mp3",
  closeSubstance: "voiceover/vo-close-substance.mp3",
  closeFinal: "voiceover/vo-close-final.mp3",

  // Variant A — winner-pattern (identity/contrarian hook)
  intro: "voiceover/vo-intro.mp3",
  bridge: "voiceover/vo-bridge.mp3",

  // Variant B — hybrid (metric-first hook)
  introB: "voiceover/vo-intro-B.mp3",
  bridgeB: "voiceover/vo-bridge-B.mp3",

  // Variant C — differentiated (5-act layout, dedicated substance + Opus beats)
  hookC: "voiceover/vo-hook-C.mp3",
  storyC: "voiceover/vo-story-C.mp3",
  synthesisC: "voiceover/vo-synthesis-C.mp3",
  opusC: "voiceover/vo-opus-C.mp3",
  depthC: "voiceover/vo-depth-C.mp3",
  closeC: "voiceover/vo-close-C.mp3",
} as const;

export type VoKey = keyof typeof VO_FILES;

/**
 * Fallback durations (seconds) keyed by VO beat. Measured 2026-04-24 from
 * Antoni renders. Used when public/ MP3 files cannot be measured at
 * metadata-resolution time (e.g. CI without public/).
 */
const FALLBACK_VO_SECONDS: Record<VoKey, number> = {
  // Shared scenario cues
  coyote: 3.66,
  sickCow: 6.5,
  calving: 5.69,
  storm: 3.66,

  // Shared market + close cues (A/B)
  market: 21.03,
  mesh: 22.6,
  closeSubstance: 12.85,
  closeFinal: 5.85,

  // Variant A
  intro: 14.45,
  bridge: 8.36,

  // Variant B
  introB: 16.25,
  bridgeB: 1.99,

  // Variant C
  hookC: 7.97,
  storyC: 27.66,
  synthesisC: 7.97,
  opusC: 24.06,
  depthC: 12.49,
  closeC: 6.71,
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

// ─── Layout constants per variant ─────────────────────────────────────────────
//
// Variant A & B share a 3-act winner-pattern skeleton (60/90/30 = 180 s).
// Variant C uses a 5-act layout (20/50/55/35/20 = 180 s).

// A & B — Act 1 (60s):
//   0–8   cold-open hook (8 s, no VO)
//   8–22  intro VO (~14-16 s)
//   22–50 market VO (~26 s, but the audio is 21 s — leaves ~7 s of music tail)
//   50–60 bridge (~2-8 s VO + tail)
const AB_ACT1_HOOK_SECONDS = 8;
const AB_ACT1_INTRO_MIN_SECONDS = 14;
const AB_ACT1_MARKET_SLOT_SECONDS = 28;
const AB_ACT1_BRIDGE_MIN_SECONDS = 10;

// A & B — Act 2 (90s):
//   0–55  five scenarios @ 11 s each
//   55–90 mesh "under the hood" reveal (35 s)
const AB_ACT2_SCENARIO_COUNT = 5;
const AB_ACT2_SCENARIO_SECONDS = 11;
const AB_ACT2_MESH_SECONDS = 35;

// A & B — Act 3 (30s):
//   0–18  substance VO + overlays
//   18–30 wordmark close
const AB_ACT3_SUBSTANCE_SECONDS = 18;
const AB_ACT3_FINAL_SECONDS = 12;

// C — Act 1 (Hook, 20s):
//   0–8   metric punch (no VO)
//   8–20  hookC VO (~12 s)
const C_ACT1_HOOK_PUNCH_SECONDS = 8;
const C_ACT1_HOOK_VO_MIN_SECONDS = 12;

// C — Act 2 (Story, 50s)
const C_ACT2_STORY_MIN_SECONDS = 46;

// C — Act 3 (Demo, 55s):
//   0–40  five scenarios @ 8 s each
//   40–55 synthesis (15 s)
const C_ACT3_SCENARIO_COUNT = 5;
const C_ACT3_SCENARIO_SECONDS = 8;
const C_ACT3_SYNTHESIS_SECONDS = 15;

// C — Act 4 (Substance, 35s):
//   0–20  Opus 4.7 + co-direction (20 s)
//   20–35 depth + ledger (15 s)
const C_ACT4_OPUS_SECONDS = 20;
const C_ACT4_DEPTH_SECONDS = 15;

// C — Act 5 (Close, 20s):
//   0–13  why-it-matters bookend (~12-13 s)
//   13–20 wordmark + sign-off (7 s)
const C_ACT5_BOOKEND_SECONDS = 13;
const C_ACT5_WORDMARK_SECONDS = 7;

// Re-exported for act components.
export const AB_LAYOUT = {
  act1: {
    hook: AB_ACT1_HOOK_SECONDS,
    introMin: AB_ACT1_INTRO_MIN_SECONDS,
    marketSlot: AB_ACT1_MARKET_SLOT_SECONDS,
    bridgeMin: AB_ACT1_BRIDGE_MIN_SECONDS,
  },
  act2: {
    scenarioCount: AB_ACT2_SCENARIO_COUNT,
    scenarioSeconds: AB_ACT2_SCENARIO_SECONDS,
    meshSeconds: AB_ACT2_MESH_SECONDS,
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
    scenarioCount: C_ACT3_SCENARIO_COUNT,
    scenarioSeconds: C_ACT3_SCENARIO_SECONDS,
    synthesisSeconds: C_ACT3_SYNTHESIS_SECONDS,
  },
  act4: {
    opusSeconds: C_ACT4_OPUS_SECONDS,
    depthSeconds: C_ACT4_DEPTH_SECONDS,
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
    // C uses 5-act layout 20/50/55/35/20 = 180 s.
    const act1Seconds = Math.max(
      C_ACT1_HOOK_PUNCH_SECONDS + Math.max(voSeconds.hookC + 0.5, C_ACT1_HOOK_VO_MIN_SECONDS),
      20,
    );
    const act2Seconds = Math.max(voSeconds.storyC + 2, 50);
    const act3Seconds =
      C_ACT3_SCENARIO_COUNT * C_ACT3_SCENARIO_SECONDS +
      C_ACT3_SYNTHESIS_SECONDS;
    const act4Seconds = C_ACT4_OPUS_SECONDS + C_ACT4_DEPTH_SECONDS;
    const act5Seconds = C_ACT5_BOOKEND_SECONDS + C_ACT5_WORDMARK_SECONDS;

    actDurations = {
      act1: framesFromSeconds(act1Seconds),
      act2: framesFromSeconds(act2Seconds),
      act3: framesFromSeconds(act3Seconds),
      act4: framesFromSeconds(act4Seconds),
      act5: framesFromSeconds(act5Seconds),
    };
  } else {
    // A & B — 3-act layout 60/90/30 = 180 s.
    // Pick the variant-specific intro/bridge for sizing.
    const introSeconds =
      variant === "B" ? voSeconds.introB : voSeconds.intro;
    const bridgeSeconds =
      variant === "B" ? voSeconds.bridgeB : voSeconds.bridge;

    const act1Seconds = Math.max(
      AB_ACT1_HOOK_SECONDS +
        Math.max(introSeconds + 0.5, AB_ACT1_INTRO_MIN_SECONDS) +
        AB_ACT1_MARKET_SLOT_SECONDS +
        Math.max(bridgeSeconds + 0.5, AB_ACT1_BRIDGE_MIN_SECONDS),
      60,
    );
    const act2Seconds =
      AB_ACT2_SCENARIO_COUNT * AB_ACT2_SCENARIO_SECONDS +
      AB_ACT2_MESH_SECONDS;
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
