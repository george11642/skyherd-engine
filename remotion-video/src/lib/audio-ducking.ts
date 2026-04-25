/**
 * audio-ducking.ts — per-stem ducking math for MusicBed.
 *
 * `useDuckingVolume` returns a frame-callback suitable for <Audio volume={fn}>
 * that implements:
 *   • 12-frame ramp DOWN before each VO window
 *   • hold at duckedGain during window
 *   • 18-frame ramp UP after each VO window ends
 *
 * Sting boost logic: while within stingActiveFrames of a sting frame,
 * normalGain is temporarily raised to boostGain (default 0.85), then
 * decays back over stingDecayFrames.
 */

import { interpolate } from "remotion";

export interface VoSegment {
  startFrame: number;
  endFrame: number;
}

export interface DuckingConfig {
  /** Nominal gain when no VO is playing (0–1) */
  normalGain: number;
  /** Gain while VO is playing (0–1) */
  duckedGain: number;
  /** Number of frames to ramp DOWN into duck before VO start */
  rampInFrames?: number;
  /** Number of frames to ramp UP out of duck after VO end */
  rampOutFrames?: number;
  /** Optional list of composition frames where stings fire */
  stingFrames?: number[];
  /** Gain boost during a sting peak */
  boostGain?: number;
  /** How many frames after a sting frame to stay at peak boost */
  stingPeakFrames?: number;
  /** How many frames after peak to decay back to normalGain */
  stingDecayFrames?: number;
}

const RAMP_IN_DEFAULT = 12;
const RAMP_OUT_DEFAULT = 18;
const STING_PEAK_DEFAULT = 7; // ~250ms at 30fps
const STING_DECAY_DEFAULT = 15; // ~500ms at 30fps
const BOOST_GAIN_DEFAULT = 0.85;

/**
 * Returns a frame-callback `(f: number) => number` suitable for
 * `<Audio volume={fn}>`.
 *
 * NOTE: when used inside a `<Sequence from={X}>`, the Audio component's
 * volume callback receives `f` relative to when the audio started, NOT the
 * composition frame.  For stems that start at frame 0 with `loop`, `f` equals
 * the composition frame.  This function therefore accepts absolute composition
 * frames and requires callers to pass `compositionFrame` (i.e. the frame
 * reported from `useCurrentFrame()` at the MusicBed level) via the closure.
 *
 * Usage inside MusicBed:
 *   const frame = useCurrentFrame();
 *   const volumeFn = makeDuckingVolumeFn(voSegments, config);
 *   <Audio volume={() => volumeFn(frame)} ... />
 */
export function makeDuckingVolumeFn(
  voSegments: VoSegment[],
  config: DuckingConfig,
): (absoluteFrame: number) => number {
  const {
    normalGain,
    duckedGain,
    rampInFrames = RAMP_IN_DEFAULT,
    rampOutFrames = RAMP_OUT_DEFAULT,
    stingFrames = [],
    boostGain = BOOST_GAIN_DEFAULT,
    stingPeakFrames = STING_PEAK_DEFAULT,
    stingDecayFrames = STING_DECAY_DEFAULT,
  } = config;

  return (absoluteFrame: number): number => {
    // --- Ducking envelope ---
    let duckRatio = 0; // 0 = no duck, 1 = fully ducked

    for (const { startFrame, endFrame } of voSegments) {
      const rampInStart = startFrame - rampInFrames;
      const rampOutEnd = endFrame + rampOutFrames;

      if (absoluteFrame < rampInStart || absoluteFrame > rampOutEnd) continue;

      // Ramp in (approaching VO)
      if (absoluteFrame < startFrame) {
        const t = interpolate(
          absoluteFrame,
          [rampInStart, startFrame],
          [0, 1],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
        );
        duckRatio = Math.max(duckRatio, t);
        continue;
      }

      // During VO
      if (absoluteFrame <= endFrame) {
        duckRatio = 1;
        continue;
      }

      // Ramp out (after VO)
      const t = interpolate(
        absoluteFrame,
        [endFrame, rampOutEnd],
        [1, 0],
        { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
      );
      duckRatio = Math.max(duckRatio, t);
    }

    const duckedVolume =
      normalGain + (duckedGain - normalGain) * duckRatio;

    // --- Sting boost (only when duckRatio < 1, i.e. not mid-VO) ---
    if (stingFrames.length === 0 || duckRatio >= 1) {
      return Math.max(0, Math.min(1, duckedVolume));
    }

    let stingBoost = 0;

    for (const sf of stingFrames) {
      const peakEnd = sf + stingPeakFrames;
      const decayEnd = peakEnd + stingDecayFrames;

      if (absoluteFrame < sf || absoluteFrame > decayEnd) continue;

      if (absoluteFrame <= peakEnd) {
        // Instant rise: interpolate from normalGain to boostGain over first 3 frames
        const t = interpolate(absoluteFrame, [sf, Math.min(sf + 3, peakEnd)], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        stingBoost = Math.max(stingBoost, t);
      } else {
        // Decay back to 0
        const t = interpolate(absoluteFrame, [peakEnd, decayEnd], [1, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        stingBoost = Math.max(stingBoost, t);
      }
    }

    const boostedNormal = normalGain + (boostGain - normalGain) * stingBoost;
    const finalVolume = boostedNormal + (duckedGain - boostedNormal) * duckRatio;
    return Math.max(0, Math.min(1, finalVolume));
  };
}
