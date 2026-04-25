/**
 * v2 Main composition — variant-aware.
 *
 * Dispatches to A / B (3-act winner-pattern) or C (5-act differentiated)
 * based on the `variant` prop. Each variant is also registered as its own
 * top-level composition (Main_A / Main_B / Main_C) in Root.tsx so renders can
 * target a specific variant via `pnpm exec remotion render Main_A …`.
 *
 * BGM bed and per-stem ducking are handled by <MusicBed> at the composition
 * root so the envelope can see all VO start/end frames in one pass.
 */
import {
  AbsoluteFill,
  Audio,
  Sequence,
  Series,
  staticFile,
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
import { MusicBed } from "./components/MusicBed";
import { type VoSegment } from "./lib/audio-ducking";

const FPS = 30;

/**
 * Derive the list of VO windows per variant.
 * Returns VoSegment[] (absolute composition frames) used by MusicBed for ducking.
 */
const computeVoSegments = (
  variant: Variant,
  vo: VoDurationsFrames,
  actDur: { act1: number; act2: number; act3: number; act4: number; act5: number },
): VoSegment[] => {
  const segs: VoSegment[] = [];

  const push = (start: number, dur: number) => {
    segs.push({ startFrame: start, endFrame: start + dur });
  };

  if (variant === "C") {
    // v5.2 polish pass — rebalanced after measuring v5.2 Chatterbox cue
    // durations (from .planning/research/v5-chatterbox-durations.txt).
    // 9-scene timeline @ 30fps, total 5460f = 182s ≈ 3:02:
    //
    // coldOpen:    0–180     (silent, 6s)
    // hook:        180–780   (cHook 19.152s, window = 20s = 600f)
    // traditional: 780–1500  (cTraditional 21.6s + comparator beat, window = 24s = 720f)
    // answer:      1500–2010 (cAnswer 16.99s, window = 17s = 510f)
    // coyote:      2010–2910 (cCoyote 29.59s, window = 30s = 900f)
    // grid:        2910–3630 (cGrid 23.52s, window = 24s = 720f)
    // mvp:         3630–4320 (cMvp 22.10s, window = 23s = 690f)
    // vision:      4320–4980 (cVision 21.55s, window = 22s = 660f)
    // aibody:      4980–5370 (cAibody 13.03s, window = 13s = 390f)
    // wordmark:    5370–5460 (silent, 3s = 90f)
    push(180,  vo.cHook);
    push(780,  vo.cTraditional);
    push(1500, vo.cAnswer);
    push(2010, vo.cCoyote);
    push(2910, vo.cGrid);
    push(3630, vo.cMvp);
    push(4320, vo.cVision);
    push(4980, vo.cAibody);
  } else {
    // A & B share skeleton; only intro key differs.
    const introDur = variant === "B" ? vo.introB : vo.intro;

    // Act 1: hook (8s no VO) → intro → market → compare.
    const HOOK = 8 * FPS;
    push(HOOK, introDur);

    const introSlot = Math.max(introDur + 15, 14 * FPS);
    const marketStart = HOOK + introSlot;
    push(marketStart, vo.market);

    const marketSlot = Math.max(vo.market + 30, 20 * FPS);
    const compareStart = HOOK + introSlot + marketSlot;
    push(compareStart, vo.compare);

    // Act 2: deep coyote VO, montage block, then mesh-opus VO.
    const a2Start = actDur.act1;
    const deepSlot = Math.max(vo.coyoteDeep + 30, 25 * FPS);
    const MONTAGE = 25 * FPS;
    push(a2Start + 60, vo.coyoteDeep);
    // Cover the entire montage block — 5 cues (sick / tank / calving / storm /
    // bridge) land somewhere in this window. Duck across the full block so VO
    // remains audible regardless of exact landing positions.
    push(a2Start + deepSlot, MONTAGE);
    const meshStart = a2Start + deepSlot + MONTAGE;
    push(meshStart + 30, vo.meshOpus);

    // Act 3: substance → meta-loop (Phase 3) → final.
    const a3Start = actDur.act1 + actDur.act2;
    push(a3Start, vo.closeSubstance);
    // MetaLoopBeat (5 s) holds vo-meta-{A|B}.mp3 — Phase 3.
    const metaStart = a3Start + 15 * FPS;
    const metaDur = variant === "B" ? vo.metaB : vo.metaA;
    push(metaStart, metaDur);
    const finalStart = a3Start + 18 * FPS;
    push(finalStart, vo.closeFinal);
  }

  return segs;
};

export const Main = ({
  variant,
  actDurations,
  voDurationsFrames,
}: MainProps) => {
  const voSegments = computeVoSegments(
    variant,
    voDurationsFrames,
    actDurations,
  );

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(10 12 16)" }}>
      {/* Phase 6 S2: layered BGM stems with per-stem ducking + 6 stings.
          Variant C uses a 9-scene structure where the default sting frames
          (calibrated for A/B) mis-fire mid-scene — suppress all stings. */}
      <MusicBed
        voSegments={voSegments}
        stingCues={variant === "C" ? [] : undefined}
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
