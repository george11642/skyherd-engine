/**
 * MusicBed.tsx — layered BGM stems with per-stem VO ducking and sting boosts.
 *
 * Stems (all sourced from public/music/):
 *   bgm-bass.mp3   — LPF 250 Hz — stays loudest under VO (light duck to ~0.40)
 *   bgm-perc.mp3   — BPF 300-3 kHz — moderate duck to ~0.30
 *   bgm-lead.mp3   — HPF 3 kHz — aggressive duck to ~0.10 (vocals vs lead clash)
 *
 * Stings (public/sfx/sting-*.mp3):
 *   sting-open         frame   30  (0:01)
 *   sting-scenario1    frame 2340  (~1:18)
 *   sting-scenario2    frame 3150  (~1:45)
 *   sting-cost         frame 1710  (~0:57)
 *   sting-meta         frame 4500  (~2:30)
 *   sting-wordmark     frame 5100  (~2:50)
 *
 * All stings are treated as one-shot SFX; their `durationInFrames` is set
 * to 90 frames (3 s) — long enough to capture the full decay even for the
 * longest sting assets.
 */

import {
  AbsoluteFill,
  Audio,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {
  type VoSegment,
  makeDuckingVolumeFn,
} from "../lib/audio-ducking";

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

export interface StingCue {
  /** Composition frame at which the sting fires */
  frame: number;
  /** Sting asset filename (relative to public/sfx/) */
  src: string;
  /** Volume for the sting one-shot (default 0.75) */
  volume?: number;
}

export interface MusicBedProps {
  /**
   * VO windows derived from the variant's act structure.
   * Each window defines the absolute composition frames where VO is audible.
   */
  voSegments: VoSegment[];
  /**
   * Optional override of sting cues.  When omitted the default 6-sting
   * schedule is used (good for all three variants at 30 fps).
   */
  stingCues?: StingCue[];
}

// ---------------------------------------------------------------------------
// Default sting schedule (frame-accurate for 30 fps, 180 s composition)
// ---------------------------------------------------------------------------

const DEFAULT_STING_CUES: StingCue[] = [
  { frame: 30,   src: "sfx/sting-open.mp3",      volume: 0.80 },
  { frame: 1710, src: "sfx/sting-cost.mp3",      volume: 0.75 },
  { frame: 2340, src: "sfx/sting-scenario1.mp3", volume: 0.75 },
  { frame: 3150, src: "sfx/sting-scenario2.mp3", volume: 0.75 },
  { frame: 4500, src: "sfx/sting-meta.mp3",      volume: 0.70 },
  { frame: 5100, src: "sfx/sting-wordmark.mp3",  volume: 0.80 },
];

// ---------------------------------------------------------------------------
// Per-stem ducking configs.
// Source asset levels: BGM raw -17 dB mean, VO raw -23 dB mean (VO is 6 dB
// quieter than BGM at source). To put VO clearly above BGM during ducking we
// need ~12 dB attenuation on stems → sum_ducked ≈ 0.18 → ~ -15 dB total.
// Sum_normal ≈ 0.55 (~ -5 dB) keeps music-only sections lively without clipping.
// ---------------------------------------------------------------------------

const BASS_CONFIG = {
  normalGain: 0.20,
  duckedGain: 0.07,
} as const;

const PERC_CONFIG = {
  normalGain: 0.18,
  duckedGain: 0.05,
} as const;

const LEAD_CONFIG = {
  normalGain: 0.20,
  duckedGain: 0.06,
} as const;

const STING_DURATION_FRAMES = 90; // 3 s at 30 fps — covers all sting assets

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export const MusicBed = ({
  voSegments,
  stingCues = DEFAULT_STING_CUES,
}: MusicBedProps) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  // Fade-in / fade-out envelope applied uniformly across all stems
  // (150 frames = 5 s, matching Phase 5 smoothstep envelope)
  const envelopeGain = Math.min(
    Math.min(1, frame / 150),
    Math.min(1, (durationInFrames - frame) / 150),
  );

  const stingFrames = stingCues.map((s) => s.frame);

  const bassFn = makeDuckingVolumeFn(voSegments, {
    ...BASS_CONFIG,
    stingFrames,
  });
  const percFn = makeDuckingVolumeFn(voSegments, {
    ...PERC_CONFIG,
    stingFrames,
  });
  const leadFn = makeDuckingVolumeFn(voSegments, {
    ...LEAD_CONFIG,
    stingFrames,
    boostGain: 0.85,
  });

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {/* --- BGM stems (looped, start at frame 0) --- */}
      <Audio
        src={staticFile("music/bgm-bass.mp3")}
        loop
        volume={() => bassFn(frame) * envelopeGain}
      />
      <Audio
        src={staticFile("music/bgm-perc.mp3")}
        loop
        volume={() => percFn(frame) * envelopeGain}
      />
      <Audio
        src={staticFile("music/bgm-lead.mp3")}
        loop
        volume={() => leadFn(frame) * envelopeGain}
      />

      {/* --- Sting one-shots --- */}
      {stingCues.map((sting) => {
        // Guard: don't attempt to play a sting beyond the composition length
        if (sting.frame >= durationInFrames) return null;
        const safeDuration = Math.min(
          STING_DURATION_FRAMES,
          durationInFrames - sting.frame,
        );
        return (
          <Sequence
            key={`sting-${sting.src}-${sting.frame}`}
            from={sting.frame}
            durationInFrames={safeDuration}
          >
            <Audio
              src={staticFile(sting.src)}
              volume={sting.volume ?? 0.75}
            />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
