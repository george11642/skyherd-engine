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
// durations. Per-variant — A/B share 60/90/30 = 180s; C is 20/50/55/35/20 = 180s.
const DEFAULT_AB_ACT_DURATIONS = {
  act1: 60 * FPS,
  act2: 90 * FPS,
  act3: 30 * FPS,
  act4: 0,
  act5: 0,
};

const DEFAULT_C_ACT_DURATIONS = {
  act1: 20 * FPS,
  act2: 50 * FPS,
  act3: 55 * FPS,
  act4: 35 * FPS,
  act5: 20 * FPS,
};

// Fallback VO durations (frames). Measured 2026-04-24 from Antoni renders.
const DEFAULT_VO_DURATIONS_FRAMES = {
  // Shared scenario cues
  coyote: Math.ceil(3.66 * FPS),
  sickCow: Math.ceil(6.5 * FPS),
  calving: Math.ceil(5.69 * FPS),
  storm: Math.ceil(3.66 * FPS),
  // Shared market + close
  market: Math.ceil(21.03 * FPS),
  mesh: Math.ceil(22.6 * FPS),
  closeSubstance: Math.ceil(12.85 * FPS),
  closeFinal: Math.ceil(5.85 * FPS),
  // Variant A
  intro: Math.ceil(14.45 * FPS),
  bridge: Math.ceil(8.36 * FPS),
  // Variant B
  introB: Math.ceil(16.25 * FPS),
  bridgeB: Math.ceil(1.99 * FPS),
  // Variant C
  hookC: Math.ceil(7.97 * FPS),
  storyC: Math.ceil(27.66 * FPS),
  synthesisC: Math.ceil(7.97 * FPS),
  opusC: Math.ceil(24.06 * FPS),
  depthC: Math.ceil(12.49 * FPS),
  closeC: Math.ceil(6.71 * FPS),
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
