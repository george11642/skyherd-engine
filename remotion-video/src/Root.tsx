import "./index.css";
import { Composition } from "remotion";
import { loadFont } from "@remotion/google-fonts/Inter";
import { Main } from "./Main";
import {
  calculateMainMetadata,
  FPS,
  HEIGHT,
  type Variant,
  WIDTH,
} from "./compositions/calculate-main-metadata";

loadFont("normal", {
  weights: ["400", "500", "600", "700", "800"],
  subsets: ["latin"],
});

// Default frame counts used before calculateMetadata measures real VO
// durations. Iter2 retunes: A/B ~60/100/30, C ~20/45/55/50/20.
const DEFAULT_AB_ACT_DURATIONS = {
  act1: 60 * FPS,
  act2: 100 * FPS,
  act3: 30 * FPS,
  act4: 0,
  act5: 0,
};

// v5.6 polish pass — exact 3:00 runtime (180s = 5400 frames @ 30fps)
// Coyote sim extended +2s (28→30) by trimming hook -1 and traditional -1.
// hook VO 20.76s → 21s window leaves only 0.24s tail (tight).
// trad VO 22.10s → 23s window leaves 0.9s for comparator slide-in tail.
const DEFAULT_C_ACT_DURATIONS = {
  act1: 27 * FPS,   //  810f: coldOpen(6s) + hook(21s)        — hook VO 20.76s
  act2: 39 * FPS,   // 1170f: traditional(23s) + answer(16s)  — trad 22.10s + comparator slide-in
  act3: 54 * FPS,   // 1620f: coyote(30s) + grid(24s)         — coyote scene extended +2s
  act4: 45 * FPS,   // 1350f: mvp(23s) + vision(22s)
  act5: 15 * FPS,   //  450f: aibody(13s) + wordmark(2s)
};
// Total: 27+39+54+45+15 = 180s = 5400 frames @ 30fps

// Fallback VO durations (frames). Measured 2026-04-24 from Inworld/Nate render.
const DEFAULT_VO_DURATIONS_FRAMES = {
  // Shared deep scenario (A/B/C)
  coyoteDeep: Math.ceil(23.09 * FPS),
  // Shared (A/B)
  market: Math.ceil(15.70 * FPS),
  compare: Math.ceil(24.82 * FPS),
  meshOpus: Math.ceil(25.29 * FPS),
  closeSubstance: Math.ceil(14.21 * FPS),
  closeFinal: Math.ceil(6.03 * FPS),
  // Variant A
  intro: Math.ceil(14.52 * FPS),
  // Variant B
  introB: Math.ceil(18.68 * FPS),
  // Variant C
  hookC: Math.ceil(12.96 * FPS),
  storyC: Math.ceil(31.63 * FPS),
  opusC: Math.ceil(27.72 * FPS),
  depthC: Math.ceil(12.28 * FPS),
  closeC: Math.ceil(7.94 * FPS),
  // Montage cues (Phase 2 — fills 1:25-1:50 silent window)
  montageSick: Math.ceil(7.92 * FPS),
  montageTank: Math.ceil(6.09 * FPS),
  montageCalving: Math.ceil(6.27 * FPS),
  montageStorm: Math.ceil(5.46 * FPS),
  montageBridge: Math.ceil(5.07 * FPS),
  // Meta-loop cues (Phase 3 — ABAct3Close MetaLoopBeat)
  metaA: Math.ceil(9.80 * FPS),
  metaB: Math.ceil(8.07 * FPS),
  // Variant C v5 — Chatterbox-cloned George voice (measured 2026-04-25 ffprobe)
  cHook: Math.ceil(19.152 * FPS),         // 575
  cTraditional: Math.ceil(13.200 * FPS),  // 396
  cAnswer: Math.ceil(15.672 * FPS),       // 471
  cCoyote: Math.ceil(22.440 * FPS),       // 674
  cGrid: Math.ceil(18.240 * FPS),         // 548
  cMvp: Math.ceil(17.304 * FPS),          // 520
  cVision: Math.ceil(12.552 * FPS),       // 377
  cAibody: Math.ceil(11.064 * FPS),       // 332
};

const sumActDurations = (a: typeof DEFAULT_AB_ACT_DURATIONS): number =>
  a.act1 + a.act2 + a.act3 + a.act4 + a.act5;

const variantDefaults = (variant: Variant) => ({
  variant,
  actDurations:
    variant === "C" ? DEFAULT_C_ACT_DURATIONS : DEFAULT_AB_ACT_DURATIONS,
  voDurationsFrames: DEFAULT_VO_DURATIONS_FRAMES,
});

export const RemotionRoot = () => {
  return (
    <>
      {/* Default — winner-pattern (A) is the recommended render. */}
      <Composition
        id="Main"
        component={Main}
        durationInFrames={sumActDurations(DEFAULT_AB_ACT_DURATIONS)}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={variantDefaults("A")}
        calculateMetadata={calculateMainMetadata}
      />
      <Composition
        id="Main-A"
        component={Main}
        durationInFrames={sumActDurations(DEFAULT_AB_ACT_DURATIONS)}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={variantDefaults("A")}
        calculateMetadata={calculateMainMetadata}
      />
      <Composition
        id="Main-B"
        component={Main}
        durationInFrames={sumActDurations(DEFAULT_AB_ACT_DURATIONS)}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={variantDefaults("B")}
        calculateMetadata={calculateMainMetadata}
      />
      <Composition
        id="Main-C"
        component={Main}
        durationInFrames={sumActDurations(DEFAULT_C_ACT_DURATIONS)}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={variantDefaults("C")}
        calculateMetadata={calculateMainMetadata}
      />
    </>
  );
};
