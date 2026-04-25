/**
 * v2 Main composition — variant-aware.
 *
 * Dispatches to A / B (3-act winner-pattern) or C (5-act differentiated)
 * based on the `variant` prop. Each variant is also registered as its own
 * top-level composition (Main_A / Main_B / Main_C) in Root.tsx so renders can
 * target a specific variant via `pnpm exec remotion render Main_A …`.
 *
 * BGM bed and ducking are handled here at the composition root so the
 * envelope can see all VO start/end frames in one pass.
 */
import {
  AbsoluteFill,
  Audio,
  Sequence,
  Series,
  staticFile,
  useVideoConfig,
} from "remotion";
import {
  type MainProps,
  type Variant,
  type VoDurationsFrames,
} from "./compositions/calculate-main-metadata";
import { ABAct1Hook } from "./acts/v2/ABAct1Hook";
import { ABAct2Demo } from "./acts/v2/ABAct2Demo";
import { ABAct3Close } from "./acts/v2/ABAct3Close";
import {
  CAct1Hook,
  CAct2Story,
  CAct3Demo,
  CAct4Substance,
  CAct5Close,
} from "./acts/v2/CActs";

const FPS = 30;
const DUCK_BASE = 0.55;
const DUCK_UNDER_VO = 0.22;
const DUCK_FADE = 24;
const DUCK_INTER_GAP = 18;

const smoothstep = (edge0: number, edge1: number, x: number): number => {
  if (edge1 === edge0) return x >= edge1 ? 1 : 0;
  const t = Math.max(0, Math.min(1, (x - edge0) / (edge1 - edge0)));
  return t * t * (3 - 2 * t);
};

const duckingCurve = (
  frame: number,
  totalFrames: number,
  duckWindows: Array<[number, number]>,
): number => {
  const envelope = Math.min(
    smoothstep(0, 150, frame),
    smoothstep(totalFrames, totalFrames - 150, frame),
  );

  let duckAmount = 0;
  for (const [start, end] of duckWindows) {
    const rampIn = smoothstep(start - DUCK_FADE, start, frame);
    const rampOut = smoothstep(end + DUCK_FADE, end, frame);
    const inWindow = Math.min(rampIn, rampOut);
    if (inWindow > duckAmount) duckAmount = inWindow;
  }

  for (let i = 0; i < duckWindows.length - 1; i++) {
    const [, endA] = duckWindows[i];
    const [startB] = duckWindows[i + 1];
    if (startB - endA <= DUCK_INTER_GAP && frame >= endA && frame <= startB) {
      duckAmount = Math.max(duckAmount, 1);
    }
  }

  const volume = DUCK_BASE + (DUCK_UNDER_VO - DUCK_BASE) * duckAmount;
  return volume * envelope;
};

// Compute the duck-window list per variant. Each entry is an absolute frame
// range when a VO file is playing — used by the BGM ducker.
const computeDuckWindows = (
  variant: Variant,
  vo: VoDurationsFrames,
  actDur: { act1: number; act2: number; act3: number; act4: number; act5: number },
): Array<[number, number]> => {
  const windows: Array<[number, number]> = [];

  if (variant === "C") {
    // Act 1: hook punch (8s no VO) then hook VO.
    const a1Start = 0;
    const a1HookPunchEnd = 8 * FPS;
    windows.push([
      a1Start + a1HookPunchEnd,
      a1Start + a1HookPunchEnd + vo.hookC,
    ]);

    // Act 2: story VO across the entire act.
    const a2Start = actDur.act1;
    windows.push([a2Start + 30, a2Start + 30 + vo.storyC]);

    // Act 3: 5 scenarios @ 8s, then synthesis.
    const a3Start = actDur.act1 + actDur.act2;
    const SCEN = 8 * FPS;
    [vo.coyote, vo.sickCow, 0, vo.calving, vo.storm].forEach((d, i) => {
      if (d > 0) {
        const start = a3Start + i * SCEN + 30;
        windows.push([start, start + d]);
      }
    });
    const synthStart = a3Start + 5 * SCEN;
    windows.push([synthStart + 30, synthStart + 30 + vo.synthesisC]);

    // Act 4: opus then depth.
    const a4Start = a3Start + actDur.act3;
    windows.push([a4Start + 30, a4Start + 30 + vo.opusC]);
    const depthStart = a4Start + 20 * FPS;
    windows.push([depthStart + 30, depthStart + 30 + vo.depthC]);

    // Act 5: bookend close.
    const a5Start = a4Start + actDur.act4;
    windows.push([a5Start + 30, a5Start + 30 + vo.closeC]);
  } else {
    // A & B share skeleton; only intro/bridge keys differ.
    const introDur = variant === "B" ? vo.introB : vo.intro;
    const bridgeDur = variant === "B" ? vo.bridgeB : vo.bridge;

    // Act 1: hook (8s no VO) → intro → market → bridge.
    const HOOK = 8 * FPS;
    const introStart = HOOK;
    windows.push([introStart, introStart + introDur]);

    // intro's slot is max(intro+0.5, 14) seconds
    const introSlot =
      Math.max(introDur / FPS + 0.5, 14) * FPS;
    const marketStart = HOOK + introSlot;
    windows.push([marketStart, marketStart + vo.market]);

    const marketSlot = 28 * FPS;
    const bridgeStart = HOOK + introSlot + marketSlot;
    windows.push([bridgeStart, bridgeStart + bridgeDur]);

    // Act 2: 5 scenarios @ 11s, then mesh.
    const a2Start = actDur.act1;
    const SCEN = 11 * FPS;
    [vo.coyote, vo.sickCow, 0, vo.calving, vo.storm].forEach((d, i) => {
      if (d > 0) {
        const start = a2Start + i * SCEN + 120;
        windows.push([start, start + d]);
      }
    });
    const meshStart = a2Start + 5 * SCEN;
    windows.push([meshStart, meshStart + vo.mesh]);

    // Act 3: substance then final.
    const a3Start = actDur.act1 + actDur.act2;
    windows.push([a3Start, a3Start + vo.closeSubstance]);
    const finalStart = a3Start + 18 * FPS;
    windows.push([finalStart, finalStart + vo.closeFinal]);
  }

  return windows;
};

export const Main = ({
  variant,
  actDurations,
  voDurationsFrames,
}: MainProps) => {
  const { durationInFrames } = useVideoConfig();
  const duckWindows = computeDuckWindows(
    variant,
    voDurationsFrames,
    actDurations,
  );

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(10 12 16)" }}>
      <Audio
        src={staticFile("music/bgm-main.mp3")}
        loop
        volume={(f) => duckingCurve(f, durationInFrames, duckWindows)}
      />

      {/* Global SFX cues — only meaningful for AB layout (scenarios at 11s
          increments inside Act 2). For C the cues are skipped — its 8s
          scenarios don't have time for SFX layering. */}
      {variant !== "C" && (
        <>
          <Sequence
            from={actDurations.act1 + 1 * 11 * FPS - 60}
            durationInFrames={120}
          >
            <Audio src={staticFile("sfx/coyote-distant.mp3")} volume={0.35} />
          </Sequence>
          <Sequence
            from={actDurations.act1 + 0 * 11 * FPS + 240}
            durationInFrames={120}
          >
            <Audio src={staticFile("sfx/drone-whir.mp3")} volume={0.45} />
          </Sequence>
          <Sequence
            from={actDurations.act1 + 1 * 11 * FPS + 180}
            durationInFrames={90}
          >
            <Audio src={staticFile("sfx/paper-rustle.mp3")} volume={0.4} />
          </Sequence>
          <Sequence
            from={actDurations.act1 + 2 * 11 * FPS + 60}
            durationInFrames={60}
          >
            <Audio src={staticFile("sfx/radio-static.mp3")} volume={0.3} />
          </Sequence>
        </>
      )}

      {variant === "C" ? (
        <Series>
          <Series.Sequence durationInFrames={actDurations.act1}>
            <CAct1Hook />
          </Series.Sequence>
          <Series.Sequence durationInFrames={actDurations.act2}>
            <CAct2Story />
          </Series.Sequence>
          <Series.Sequence durationInFrames={actDurations.act3}>
            <CAct3Demo />
          </Series.Sequence>
          <Series.Sequence durationInFrames={actDurations.act4}>
            <CAct4Substance />
          </Series.Sequence>
          <Series.Sequence durationInFrames={actDurations.act5}>
            <CAct5Close />
          </Series.Sequence>
        </Series>
      ) : (
        <Series>
          <Series.Sequence durationInFrames={actDurations.act1}>
            <ABAct1Hook
              variant={variant}
              voDurationsFrames={voDurationsFrames}
            />
          </Series.Sequence>
          <Series.Sequence durationInFrames={actDurations.act2}>
            <ABAct2Demo />
          </Series.Sequence>
          <Series.Sequence durationInFrames={actDurations.act3}>
            <ABAct3Close />
          </Series.Sequence>
        </Series>
      )}
    </AbsoluteFill>
  );
};
