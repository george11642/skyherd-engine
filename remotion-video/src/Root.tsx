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

const DEFAULT_C_ACT_DURATIONS = {
  act1: 24 * FPS,
  act2: 45 * FPS,
  act3: 55 * FPS,
  act4: 50 * FPS,
  act5: 20 * FPS,
};

// Fallback VO durations (frames). Measured 2026-04-24 from iter2 Will/v3.
const DEFAULT_VO_DURATIONS_FRAMES = {
  // Shared deep scenario (A/B/C)
  coyoteDeep: Math.ceil(28.53 * FPS),
  // Shared (A/B)
  market: Math.ceil(17.95 * FPS),
  compare: Math.ceil(30.85 * FPS),
  meshOpus: Math.ceil(30.43 * FPS),
  closeSubstance: Math.ceil(16.93 * FPS),
  closeFinal: Math.ceil(7.24 * FPS),
  // Variant A
  intro: Math.ceil(13.64 * FPS),
  // Variant B
  introB: Math.ceil(19.88 * FPS),
  // Variant C
  hookC: Math.ceil(14.45 * FPS),
  storyC: Math.ceil(42.68 * FPS),
  opusC: Math.ceil(30.85 * FPS),
  depthC: Math.ceil(17.63 * FPS),
  closeC: Math.ceil(9.17 * FPS),
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
