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
 * Voiceover files, keyed by logical beat. Each maps to a file in
 * public/voiceover/*.mp3 that Phase 1 produced via ElevenLabs.
 */
export const VO_FILES = {
  georgeHook: "voiceover/wes-george-hook.mp3",
  establish: "voiceover/wes-establish.mp3",
  coyote: "voiceover/wes-coyote.mp3",
  sickCow: "voiceover/wes-sick-cow.mp3",
  calving: "voiceover/wes-calving.mp3",
  storm: "voiceover/wes-storm.mp3",
  synthesis: "voiceover/wes-synthesis.mp3",
  attest: "voiceover/wes-attest.mp3",
  why: "voiceover/wes-why.mp3",
  close: "voiceover/wes-close.mp3",
} as const;

export type VoKey = keyof typeof VO_FILES;

/**
 * Fallback durations (seconds) keyed by VO beat. Used only if the MP3 file
 * cannot be measured at metadata-resolution time (e.g. CI without public/).
 */
const FALLBACK_VO_SECONDS: Record<VoKey, number> = {
  georgeHook: 7.52,
  establish: 5.56,
  coyote: 3.53,
  sickCow: 5.7,
  calving: 4.26,
  storm: 3.29,
  synthesis: 19.41,
  attest: 14.76,
  why: 8.67,
  close: 2.46,
};

export type VoDurationsFrames = Record<VoKey, number>;

/**
 * Act-level durations in frames. Computed in calculateMainMetadata and passed
 * to Main so each act sub-composition knows its slot length.
 */
export type ActDurations = {
  act1: number;
  act2: number;
  act3: number;
};

export type MainProps = {
  actDurations: ActDurations;
  voDurationsFrames: VoDurationsFrames;
};

// ───── Act layout constants (seconds, local-act frames) ──────────────────────
// Act 1 beats (0..25s):
//   0–3   black card typewriter (fixed 3 s)
//   3–8   crossfade → establish clip (fixed 5 s)
//   8–18  kinetic-typography George replacement (uses george-hook VO)
//  18–24  dashboard pitch with wordmark reveal (fixed 6 s)
//  24–25  hold / fade (1 s)
export const ACT1_FIXED_SECONDS = 3 + 5 + 6 + 1; // 15 s fixed
// dynamic portion = georgeHook VO (~7.5 s) padded so beat is at least 10 s
const ACT1_GEORGE_MIN_SECONDS = 10;

// Act 2 beats (0..115s):
//   0–13  establish (fixed slot 13 s)
//   13–27  coyote scenario (14 s)
//   27–41  sick cow (14 s)
//   41–55  water (14 s)
//   55–69  calving (14 s)
//   69–83  storm (14 s)
//   83–115 synthesis (32 s; uses synthesis VO plus padding)
export const ACT2_ESTABLISH_SECONDS = 13;
export const ACT2_SCENARIO_SECONDS = 14;
export const ACT2_SCENARIO_COUNT = 5;
// synthesis beat duration = max(synthesis VO + 2 s padding, 28 s)
const ACT2_SYNTHESIS_MIN_SECONDS = 28;

// Act 3 beats (0..40s):
//   0–20  split-screen attestation (uses attest VO ~14.76 s; 20 s slot)
//   20–35  kinetic-typography "Why it matters" (uses why VO ~8.67 s; 15 s slot)
//   35–40  final close card (uses close VO ~2.46 s; 5 s slot)
export const ACT3_ATTEST_SECONDS = 20;
export const ACT3_WHY_SECONDS = 15;
export const ACT3_CLOSE_SECONDS = 5;

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

export const calculateMainMetadata: CalculateMetadataFunction<
  MainProps
> = async ({ props }) => {
  // Measure every VO file in parallel.
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

  // ── Act 1 total ───────────────────────────────────────────────────────────
  const act1GeorgeSeconds = Math.max(
    voSeconds.georgeHook + 0.5,
    ACT1_GEORGE_MIN_SECONDS,
  );
  const act1Seconds = ACT1_FIXED_SECONDS + act1GeorgeSeconds;

  // ── Act 2 total ───────────────────────────────────────────────────────────
  const act2SynthesisSeconds = Math.max(
    voSeconds.synthesis + 2,
    ACT2_SYNTHESIS_MIN_SECONDS,
  );
  const act2Seconds =
    ACT2_ESTABLISH_SECONDS +
    ACT2_SCENARIO_COUNT * ACT2_SCENARIO_SECONDS +
    act2SynthesisSeconds;

  // ── Act 3 total ───────────────────────────────────────────────────────────
  const act3Seconds =
    ACT3_ATTEST_SECONDS + ACT3_WHY_SECONDS + ACT3_CLOSE_SECONDS;

  const act1 = framesFromSeconds(act1Seconds);
  const act2 = framesFromSeconds(act2Seconds);
  const act3 = framesFromSeconds(act3Seconds);
  const total = act1 + act2 + act3;

  return {
    durationInFrames: total,
    props: {
      ...props,
      actDurations: { act1, act2, act3 },
      voDurationsFrames,
    },
  };
};
