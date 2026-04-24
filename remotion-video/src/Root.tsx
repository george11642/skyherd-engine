import "./index.css";
import { Composition } from "remotion";
import { loadFont } from "@remotion/google-fonts/Inter";
import { Main } from "./Main";
import {
  calculateMainMetadata,
  FPS,
  HEIGHT,
  WIDTH,
} from "./compositions/calculate-main-metadata";

// Preload Inter with the weights used across the composition.
loadFont("normal", {
  weights: ["400", "500", "600", "700", "800"],
  subsets: ["latin"],
});

// Placeholder durations (in frames) overridden by calculateMetadata once the
// VO MP3s in public/voiceover are measured. Match the locked act plan:
// Act 1 ≈ 25 s, Act 2 ≈ 115 s, Act 3 ≈ 40 s → 180 s total.
const DEFAULT_ACT_DURATIONS = {
  act1: 25 * FPS,
  act2: 115 * FPS,
  act3: 40 * FPS,
};

const DEFAULT_VO_DURATIONS_FRAMES = {
  georgeHook: Math.ceil(7.52 * FPS),
  establish: Math.ceil(5.56 * FPS),
  coyote: Math.ceil(3.53 * FPS),
  sickCow: Math.ceil(5.7 * FPS),
  calving: Math.ceil(4.26 * FPS),
  storm: Math.ceil(3.29 * FPS),
  synthesis: Math.ceil(19.41 * FPS),
  attest: Math.ceil(14.76 * FPS),
  why: Math.ceil(8.67 * FPS),
  close: Math.ceil(2.46 * FPS),
};

const DEFAULT_TOTAL_DURATION =
  DEFAULT_ACT_DURATIONS.act1 +
  DEFAULT_ACT_DURATIONS.act2 +
  DEFAULT_ACT_DURATIONS.act3;

export const RemotionRoot = () => {
  return (
    <>
      <Composition
        id="Main"
        component={Main}
        durationInFrames={DEFAULT_TOTAL_DURATION}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={{
          actDurations: DEFAULT_ACT_DURATIONS,
          voDurationsFrames: DEFAULT_VO_DURATIONS_FRAMES,
        }}
        calculateMetadata={calculateMainMetadata}
      />
    </>
  );
};
