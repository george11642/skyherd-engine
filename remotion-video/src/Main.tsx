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
import { KineticCaptions } from "./components/KineticCaptions";
import { LottieReveal } from "./components/LottieReveal";

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

// Compute the duck-window list per variant. Iter2 restructure: deep coyote
// scenario, silent 4-scenario montage, compare beat in Act 1 (A/B) or Act 2
// (C), mesh-opus beat that names Opus 4.7 explicitly.
const computeDuckWindows = (
  variant: Variant,
  vo: VoDurationsFrames,
  actDur: { act1: number; act2: number; act3: number; act4: number; act5: number },
): Array<[number, number]> => {
  const windows: Array<[number, number]> = [];

  if (variant === "C") {
    // Act 1: hook punch (8s no VO) then hookC VO.
    const a1HookPunchEnd = 8 * FPS;
    windows.push([a1HookPunchEnd, a1HookPunchEnd + vo.hookC]);

    // Act 2: story VO (which now folds the compare beat in).
    const a2Start = actDur.act1;
    windows.push([a2Start + 30, a2Start + 30 + vo.storyC]);

    // Act 3: deep coyote (VO), then silent montage, then silent synthesis.
    const a3Start = actDur.act1 + actDur.act2;
    windows.push([a3Start + 60, a3Start + 60 + vo.coyoteDeep]);

    // Act 4: opus then depth.
    const a4Start = a3Start + actDur.act3;
    const opusSlot = Math.max(vo.opusC + FPS, 25 * FPS);
    windows.push([a4Start + 30, a4Start + 30 + vo.opusC]);
    const depthStart = a4Start + opusSlot;
    windows.push([depthStart + 30, depthStart + 30 + vo.depthC]);

    // Act 5: bookend close.
    const a5Start = a4Start + actDur.act4;
    windows.push([a5Start + 30, a5Start + 30 + vo.closeC]);
  } else {
    // A & B share skeleton; only intro key differs. Act 1 has no bridge
    // cue in iter2 — replaced by the compare beat VO.
    const introDur = variant === "B" ? vo.introB : vo.intro;

    // Act 1: hook (8s no VO) → intro → market → compare.
    const HOOK = 8 * FPS;
    const introStart = HOOK;
    windows.push([introStart, introStart + introDur]);

    const introSlot = Math.max(introDur + 15, 14 * FPS);
    const marketStart = HOOK + introSlot;
    windows.push([marketStart, marketStart + vo.market]);

    const marketSlot = Math.max(vo.market + 30, 20 * FPS);
    const compareStart = HOOK + introSlot + marketSlot;
    windows.push([compareStart, compareStart + vo.compare]);

    // Act 2: deep coyote VO, then silent montage, then mesh-opus VO.
    const a2Start = actDur.act1;
    const deepSlot = Math.max(vo.coyoteDeep + 30, 25 * FPS);
    const MONTAGE = 25 * FPS;
    windows.push([a2Start + 60, a2Start + 60 + vo.coyoteDeep]);
    const meshStart = a2Start + deepSlot + MONTAGE;
    windows.push([meshStart + 30, meshStart + 30 + vo.meshOpus]);

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

      {/* Global SFX cues — iter2 restructure places them during the deep
          coyote beat and across the silent montage. Deep coyote runs ~25s
          at the start of Act 2 (A/B) or Act 3 (C). SFX timing is relative
          to the appropriate act start. */}
      {variant !== "C" && (
        <>
          {/* Coyote-distant inside deep coyote beat (around tool-call flash) */}
          <Sequence
            from={actDurations.act1 + 3 * FPS}
            durationInFrames={120}
          >
            <Audio src={staticFile("sfx/coyote-distant.mp3")} volume={0.35} />
          </Sequence>
          {/* Drone whir when telemetry overlay slides in */}
          <Sequence
            from={actDurations.act1 + 9 * FPS}
            durationInFrames={180}
          >
            <Audio src={staticFile("sfx/drone-whir.mp3")} volume={0.4} />
          </Sequence>
          {/* Paper-rustle on sick-cow vet-packet callout (montage scene 1) */}
          <Sequence
            from={actDurations.act1 + 26 * FPS}
            durationInFrames={90}
          >
            <Audio src={staticFile("sfx/paper-rustle.mp3")} volume={0.4} />
          </Sequence>
          {/* Radio-static on calving priority-page (montage scene 3) */}
          <Sequence
            from={actDurations.act1 + 38 * FPS}
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

      {/* Phase E2 Lottie reveals — iter2: one deep coyote scenario (25s at
          start of Act 2 for A/B, Act 3 for C) + 4-scenario montage (~6s each)
          + mesh/opus beat. Fail-soft via LottieReveal's null-on-404 guard. */}
      {variant !== "C" ? (
        <>
          {/* Deep coyote: map pin at start, pulse wave during tool-call flash,
              hash chip on attestation at the end of the beat */}
          <Sequence
            from={actDurations.act1 + 1 * FPS}
            durationInFrames={45}
          >
            <LottieReveal asset="map-pin-drop.json" size={200} top={140} right={140} />
          </Sequence>
          <Sequence
            from={actDurations.act1 + 5 * FPS}
            durationInFrames={90}
          >
            <LottieReveal asset="pulse-wave.json" size={220} top={780} left={140} loop />
          </Sequence>
          <Sequence
            from={actDurations.act1 + 22 * FPS}
            durationInFrames={75}
          >
            <LottieReveal asset="hash-chip-slide.json" size={260} top={140} left={140} />
          </Sequence>
          {/* Montage: pin drop on each of the 4 fast cuts */}
          {[0, 1, 2, 3].map((i) => (
            <Sequence
              key={`m-pin-${i}`}
              from={actDurations.act1 + 25 * FPS + i * 6 * FPS}
              durationInFrames={45}
            >
              <LottieReveal asset="map-pin-drop.json" size={160} top={140} right={140} />
            </Sequence>
          ))}
          {/* Stat counter near the cost ticker in mesh-opus beat */}
          <Sequence
            from={actDurations.act1 + actDurations.act2 - 10 * FPS}
            durationInFrames={90}
          >
            <LottieReveal asset="stat-counter.json" size={300} bottom={220} right={140} />
          </Sequence>
          {/* Checkmark complete at end of montage */}
          <Sequence
            from={actDurations.act1 + 48 * FPS}
            durationInFrames={45}
          >
            <LottieReveal asset="check-complete.json" size={140} top={300} right={140} />
          </Sequence>
        </>
      ) : (
        <>
          {/* C variant iter2: deep coyote at start of Act 3, then montage */}
          <Sequence
            from={actDurations.act1 + actDurations.act2 + 1 * FPS}
            durationInFrames={45}
          >
            <LottieReveal asset="map-pin-drop.json" size={200} top={140} right={140} />
          </Sequence>
          <Sequence
            from={actDurations.act1 + actDurations.act2 + 5 * FPS}
            durationInFrames={90}
          >
            <LottieReveal asset="pulse-wave.json" size={200} top={780} left={140} loop />
          </Sequence>
          <Sequence
            from={actDurations.act1 + actDurations.act2 + 22 * FPS}
            durationInFrames={75}
          >
            <LottieReveal asset="hash-chip-slide.json" size={260} top={140} left={140} />
          </Sequence>
          {[0, 1, 2, 3].map((i) => (
            <Sequence
              key={`c-m-pin-${i}`}
              from={actDurations.act1 + actDurations.act2 + 25 * FPS + i * 6 * FPS}
              durationInFrames={45}
            >
              <LottieReveal asset="map-pin-drop.json" size={160} top={140} right={140} />
            </Sequence>
          ))}
          {/* Stat counter during Act 4 Opus 4.7 beat */}
          <Sequence
            from={actDurations.act1 + actDurations.act2 + actDurations.act3 + 60}
            durationInFrames={120}
          >
            <LottieReveal asset="stat-counter.json" size={280} bottom={220} right={140} />
          </Sequence>
        </>
      )}

      {/* Phase E1 — kinetic captions overlay (sparse for A/B, dense for C). */}
      <KineticCaptions variant={variant} />
    </AbsoluteFill>
  );
};
