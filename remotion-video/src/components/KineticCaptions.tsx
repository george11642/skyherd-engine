/**
 * KineticCaptions — phase E1 caption overlay for the v2 demo video.
 *
 * Reads ``public/captions/captions-{A,B,C}.json`` (produced by
 * ``scripts/generate_kinetic_captions.py``) and renders the words on top of
 * the composition.
 *
 * Two modes:
 *
 *   * ``sparse`` — variants A and B. Only the emphasis windows declared in
 *     the variant scripts are rendered. Each window pops on at the second
 *     listed in the script and fades after a short dwell.
 *
 *   * ``dense`` — variant C. Every spoken word from the VO bus is rendered
 *     in a rolling 7-word window pinned 96 px from the bottom-safe margin,
 *     line-broken on punctuation.
 *
 * Style: Inter SemiBold 56 px white on a 60%-opacity black pill. Cap of 7
 * words on screen at once; new lines start after a comma or period.
 */
import {
  AbsoluteFill,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { useEffect, useState } from "react";

export type CaptionsVariant = "A" | "B" | "C";

export type SparseEmphasis = {
  /** seconds (relative to composition start) at which this window fires */
  second: number;
  /** punch text — may include punctuation; line-breaks on commas/periods */
  text: string;
};

export type DenseWord = {
  word: string;
  /** seconds, absolute timeline */
  start: number;
  end: number;
};

export type DenseSegment = {
  start: number;
  end: number;
  text: string;
  words: DenseWord[];
};

export type CaptionsPayload = {
  variant: CaptionsVariant;
  mode: "sparse" | "dense";
  emphasis: SparseEmphasis[];
  segments: DenseSegment[];
  fingerprint: string;
};

const EMPTY_PAYLOAD: CaptionsPayload = {
  variant: "A",
  mode: "sparse",
  emphasis: [],
  segments: [],
  fingerprint: "",
};

const DENSE_WINDOW_WORDS = 7;
const SPARSE_DWELL_FRAMES = 60; // 2 s @ 30 fps
const SPARSE_FADE_FRAMES = 12;

// ─── Pill container ─────────────────────────────────────────────────────────

type PillProps = {
  children: React.ReactNode;
  opacity: number;
};

const Pill = ({ children, opacity }: PillProps) => (
  <div
    style={{
      position: "absolute",
      bottom: 96,
      left: "50%",
      transform: "translateX(-50%)",
      maxWidth: "82%",
      padding: "22px 38px",
      backgroundColor: "rgba(10,12,16,0.6)",
      borderRadius: 14,
      backdropFilter: "blur(10px)",
      fontFamily: "Inter, sans-serif",
      fontWeight: 600,
      fontSize: 56,
      lineHeight: 1.18,
      letterSpacing: "-0.005em",
      color: "rgb(255,255,255)",
      textAlign: "center",
      textShadow: "0 4px 16px rgba(0,0,0,0.5)",
      opacity,
      pointerEvents: "none",
    }}
  >
    {children}
  </div>
);

// ─── Sparse mode: emphasis-window punch words ──────────────────────────────

type SparseEmphasisProps = {
  emphasis: SparseEmphasis;
  fps: number;
};

const SparseEmphasisPill = ({ emphasis, fps }: SparseEmphasisProps) => {
  const frame = useCurrentFrame();
  const startFrame = Math.round(emphasis.second * fps);
  const localFrame = frame - startFrame;

  if (localFrame < 0 || localFrame > SPARSE_DWELL_FRAMES + SPARSE_FADE_FRAMES) {
    return null;
  }

  const fadeIn = spring({
    frame: localFrame,
    fps,
    config: { damping: 90, stiffness: 200 },
  });
  const fadeOut = interpolate(
    localFrame,
    [SPARSE_DWELL_FRAMES, SPARSE_DWELL_FRAMES + SPARSE_FADE_FRAMES],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const opacity = Math.min(fadeIn, fadeOut);

  return <Pill opacity={opacity}>{emphasis.text}</Pill>;
};

// ─── Dense mode: rolling 7-word window ─────────────────────────────────────

const flattenWords = (segments: DenseSegment[]): DenseWord[] => {
  const out: DenseWord[] = [];
  for (const seg of segments) {
    for (const w of seg.words) {
      out.push(w);
    }
  }
  return out;
};

const buildLine = (words: DenseWord[]): string => {
  return words
    .map((w) => w.word.trim())
    .filter(Boolean)
    .join(" ")
    .replace(/\s+([,.!?])/g, "$1");
};

type DenseProps = {
  segments: DenseSegment[];
  fps: number;
};

const DenseRollingWindow = ({ segments, fps }: DenseProps) => {
  const frame = useCurrentFrame();
  const seconds = frame / fps;
  const allWords = flattenWords(segments);

  // Find the last word that has started by `seconds`.
  let endIdx = -1;
  for (let i = 0; i < allWords.length; i++) {
    if (allWords[i].start <= seconds) {
      endIdx = i;
    } else {
      break;
    }
  }
  if (endIdx < 0) return null;

  // Anchor the window: walk back at most 7 words OR until a sentence break.
  let startIdx = Math.max(0, endIdx - DENSE_WINDOW_WORDS + 1);
  for (let i = endIdx - 1; i >= startIdx; i--) {
    if (/[.!?]$/.test(allWords[i].word.trim())) {
      startIdx = i + 1;
      break;
    }
  }

  const window = allWords.slice(startIdx, endIdx + 1);
  if (window.length === 0) return null;

  // Fade out a beat after the last word ends.
  const lastEnd = window[window.length - 1].end;
  const opacity = interpolate(
    seconds,
    [lastEnd, lastEnd + 0.4],
    [1, 0.92],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  return <Pill opacity={opacity}>{buildLine(window)}</Pill>;
};

// ─── Top-level component ───────────────────────────────────────────────────

export type KineticCaptionsProps = {
  variant: CaptionsVariant;
  /** Optional pre-loaded payload — useful in tests / SSR. */
  payload?: CaptionsPayload;
};

export const KineticCaptions = ({
  variant,
  payload: providedPayload,
}: KineticCaptionsProps) => {
  const { fps } = useVideoConfig();
  const [payload, setPayload] = useState<CaptionsPayload>(
    providedPayload ?? EMPTY_PAYLOAD,
  );

  useEffect(() => {
    if (providedPayload) {
      setPayload(providedPayload);
      return;
    }
    let cancelled = false;
    fetch(staticFile(`captions/captions-${variant}.json`))
      .then((r) => r.json() as Promise<CaptionsPayload>)
      .then((data) => {
        if (!cancelled) setPayload(data);
      })
      .catch(() => {
        // Captions are decorative; never crash the render on a bad fetch.
      });
    return () => {
      cancelled = true;
    };
  }, [variant, providedPayload]);

  if (payload.mode === "sparse") {
    return (
      <AbsoluteFill style={{ pointerEvents: "none" }}>
        {payload.emphasis.map((e, i) => (
          <Sequence
            key={`emph-${i}-${e.second}`}
            from={Math.max(0, Math.round(e.second * fps) - 2)}
            durationInFrames={SPARSE_DWELL_FRAMES + SPARSE_FADE_FRAMES + 4}
          >
            <SparseEmphasisPill emphasis={e} fps={fps} />
          </Sequence>
        ))}
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <DenseRollingWindow segments={payload.segments} fps={fps} />
    </AbsoluteFill>
  );
};
