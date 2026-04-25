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

// v4 Wave 2C: fixed 5-act grouping — 18+34+58+42+28 = 180s = 5400 frames
const DEFAULT_C_ACT_DURATIONS = {
  act1: 18 * FPS,  // coldOpen(3s) + hook(15s)
  act2: 34 * FPS,  // traditional(17s) + answer(17s)
  act3: 58 * FPS,  // coyote(40s) + grid(18s)
  act4: 42 * FPS,  // mvp(20s) + vision(22s)
  act5: 28 * FPS,  // aibody(23s) + wordmark(5s)
};

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
  // Variant C v4 — 9-scene rewrite (Wave 2C, measured 2026-04-24 ffprobe)
  cHook: Math.ceil(14.628571 * FPS),
  cTraditional: Math.ceil(11.728980 * FPS),
  cAnswer: Math.ceil(12.747755 * FPS),
  cCoyote: Math.ceil(16.431020 * FPS),
  cGrid: Math.ceil(15.934694 * FPS),
  cMvp: Math.ceil(18.128980 * FPS),
  cVision: Math.ceil(12.538776 * FPS),
  cAibody: Math.ceil(12.826122 * FPS),
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
