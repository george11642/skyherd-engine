import {
  AbsoluteFill,
  Audio,
  Sequence,
  Series,
  interpolate,
  staticFile,
  useVideoConfig,
} from "remotion";
import { Act1Hook } from "./acts/Act1Hook";
import { Act2Demo } from "./acts/Act2Demo";
import { Act3Close } from "./acts/Act3Close";
import type { MainProps } from "./compositions/calculate-main-metadata";

// Absolute frame markers (computed at runtime inside BgmTrack / SfxTrack).
// Using act durations so we can anchor SFX to act-relative cues without the
// Act components needing to know about global timeline coordinates.

// Volume curve for the BGM music bed. Louder when no VO is speaking, duck
// to ~0.25 when Wes is on mic.
const duckingCurve = (
  frame: number,
  totalFrames: number,
  duckWindows: Array<[number, number]>,
): number => {
  const fps = 30;

  // Fade in over the first 150 frames (5 s).
  const fadeIn = interpolate(frame, [0, 150], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Fade out over the last 150 frames (5 s).
  const fadeOut = interpolate(
    frame,
    [totalFrames - 150, totalFrames],
    [1, 0],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    },
  );

  const envelope = Math.min(fadeIn, fadeOut);

  // Base volume drops when any VO window is active.
  const isDucked = duckWindows.some(
    ([start, end]) => frame >= start && frame <= end,
  );
  const base = isDucked ? 0.25 : 0.55;

  // Short cross-fade into/out of each duck window (~10 frames) to avoid clicks.
  const FADE = 10;
  let smooth = base;
  for (const [start, end] of duckWindows) {
    if (frame >= start - FADE && frame <= start) {
      smooth = interpolate(frame, [start - FADE, start], [0.55, 0.25], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
    } else if (frame >= end && frame <= end + FADE) {
      smooth = interpolate(frame, [end, end + FADE], [0.25, 0.55], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
    }
  }
  if (!isDucked && smooth === base) {
    smooth = base;
  }

  // Suppress unused-param lint
  void fps;

  return smooth * envelope;
};

export const Main = ({ actDurations, voDurationsFrames }: MainProps) => {
  const { durationInFrames } = useVideoConfig();

  // Compute absolute frame offsets for act boundaries.
  const act1Start = 0;
  const act2Start = actDurations.act1;
  const act3Start = actDurations.act1 + actDurations.act2;

  // ── Duck windows (absolute frames) ────────────────────────────────────────
  // Act 1:
  //   georgeHook VO starts 8 s into Act 1.
  //   dashboard pitch overlay uses wordmark sfx, no VO here.
  const act1GeorgeStart = act1Start + 8 * 30;
  const act1GeorgeEnd = act1GeorgeStart + voDurationsFrames.georgeHook;

  // Act 2:
  //   establish VO at local frame 0 of Act 2.
  //   each scenario has its VO cue at local frame ~300 (10 s) of the 14-s beat.
  //   synthesis VO at local frame 0 of synthesis beat.
  const act2EstablishFrames = 13 * 30;
  const scenarioFrames = 14 * 30;
  const act2EstablishStart = act2Start;
  const act2EstablishEnd = act2EstablishStart + voDurationsFrames.establish;

  const scenarioStart = (index: number) =>
    act2Start + act2EstablishFrames + index * scenarioFrames;

  const coyoteVoStart = scenarioStart(0) + 300;
  const coyoteVoEnd = coyoteVoStart + voDurationsFrames.coyote;
  const sickCowVoStart = scenarioStart(1) + 300;
  const sickCowVoEnd = sickCowVoStart + voDurationsFrames.sickCow;
  // (water scenario has no dedicated VO, lower-third only)
  const calvingVoStart = scenarioStart(3) + 300;
  const calvingVoEnd = calvingVoStart + voDurationsFrames.calving;
  const stormVoStart = scenarioStart(4) + 300;
  const stormVoEnd = stormVoStart + voDurationsFrames.storm;

  const synthesisStart = scenarioStart(5);
  const synthesisVoEnd = synthesisStart + voDurationsFrames.synthesis;

  // Act 3:
  //   attest VO at local frame 0.
  //   why VO at local frame 0 of the why beat (20 s into Act 3).
  //   close VO at local frame 0 of the close beat (35 s into Act 3).
  const attestVoStart = act3Start;
  const attestVoEnd = attestVoStart + voDurationsFrames.attest;
  const whyVoStart = act3Start + 20 * 30;
  const whyVoEnd = whyVoStart + voDurationsFrames.why;
  const closeVoStart = act3Start + 35 * 30;
  const closeVoEnd = closeVoStart + voDurationsFrames.close;

  const duckWindows: Array<[number, number]> = [
    [act1GeorgeStart, act1GeorgeEnd],
    [act2EstablishStart, act2EstablishEnd],
    [coyoteVoStart, coyoteVoEnd],
    [sickCowVoStart, sickCowVoEnd],
    [calvingVoStart, calvingVoEnd],
    [stormVoStart, stormVoEnd],
    [synthesisStart, synthesisVoEnd],
    [attestVoStart, attestVoEnd],
    [whyVoStart, whyVoEnd],
    [closeVoStart, closeVoEnd],
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(10 12 16)" }}>
      {/* Composition-wide music bed. Loops the 61-s ambient track over 180 s. */}
      <Audio
        src={staticFile("music/bgm-main.mp3")}
        loop
        volume={(f) => duckingCurve(f, durationInFrames, duckWindows)}
      />

      {/* Global SFX cues at absolute timeline positions. */}
      {/* Coyote deterrent drone-whir at scenario 1 local frame 240 (0:46 in final). */}
      <Sequence from={scenarioStart(0) + 240} durationInFrames={120}>
        <Audio src={staticFile("sfx/drone-whir.mp3")} volume={0.45} />
      </Sequence>
      {/* Distant coyote howl under scenario 1 intro. */}
      <Sequence from={scenarioStart(0) + 30} durationInFrames={120}>
        <Audio src={staticFile("sfx/coyote-distant.mp3")} volume={0.35} />
      </Sequence>
      {/* Vet paper rustle for scenario 2. */}
      <Sequence from={scenarioStart(1) + 270} durationInFrames={90}>
        <Audio src={staticFile("sfx/paper-rustle.mp3")} volume={0.4} />
      </Sequence>
      {/* Radio static for scenario 3 (water alert). */}
      <Sequence from={scenarioStart(2) + 60} durationInFrames={60}>
        <Audio src={staticFile("sfx/radio-static.mp3")} volume={0.3} />
      </Sequence>
      {/* UI ticks at each scenario's lower-third trigger (~frame 150 local). */}
      {[0, 1, 2, 3, 4].map((i) => (
        <Sequence
          key={`ui-tick-${i}`}
          from={scenarioStart(i) + 150}
          durationInFrames={20}
        >
          <Audio src={staticFile("sfx/ui-tick.mp3")} volume={0.55} />
        </Sequence>
      ))}
      {/* Keyboard-type loop under Act 3 attestation split-screen (20 s). */}
      <Sequence from={act3Start} durationInFrames={20 * 30}>
        <Audio
          src={staticFile("sfx/keyboard-type.mp3")}
          volume={0.25}
          loop
        />
      </Sequence>

      {/* Three acts in series. */}
      <Series>
        <Series.Sequence durationInFrames={actDurations.act1}>
          <Act1Hook voDurationsFrames={voDurationsFrames} />
        </Series.Sequence>
        <Series.Sequence durationInFrames={actDurations.act2}>
          <Act2Demo voDurationsFrames={voDurationsFrames} />
        </Series.Sequence>
        <Series.Sequence durationInFrames={actDurations.act3}>
          <Act3Close voDurationsFrames={voDurationsFrames} />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};
