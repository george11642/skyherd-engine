/**
 * KineticCaptions — phase E1 + G caption overlay for the v2 demo video.
 *
 * Reads ``public/captions/captions-{A,B,C}.json`` (produced by
 * ``scripts/generate_kinetic_captions.py``) and renders the words on top of
 * the composition.
 *
 * Two transcription modes (Phase E1):
 *
 *   * ``sparse`` — variants A and B. Only the emphasis windows declared in
 *     the variant scripts are rendered. Each window pops on at the second
 *     listed in the script and fades after a short dwell.
 *
 *   * ``dense`` — variant C. Every spoken word from the VO bus is rendered
 *     in a rolling 7-word window pinned 96 px from the bottom-safe margin,
 *     line-broken on punctuation.
 *
 * One AI-directed mode (Phase G):
 *
 *   * ``styled`` — when ``styled-captions-{A,B,C}.json`` is present (output
 *     of ``make video-style-captions``), Claude Opus 4.7 has selected per-
 *     word color, weight, animation, and emphasis level. The component
 *     applies them to each word: emphasis_level=3 words go all-caps and
 *     larger; animations map to fade/pop/pulse/scale/glow.
 *
 * Fallback chain: styled → plain → empty (never throws). If the styled
 * file 404s or fails to parse, the component silently falls back to plain.
 *
 * Default style: Inter SemiBold 56 px white on a 60%-opacity black pill.
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

// Phase G — Opus 4.7 styled per-word output.

export type StyledAnimation = "fade" | "pop" | "pulse" | "scale" | "glow";
export type StyledWeight = "normal" | "bold" | "black";

export type StyledWord = {
  word: string;
  start: number;
  end: number;
  segment_id: number;
  color: string; // hex
  weight: StyledWeight;
  animation: StyledAnimation;
  emphasis_level: 0 | 1 | 2 | 3;
};

export type StyledCaptionsPayload = {
  variant: CaptionsVariant;
  mode: "styled";
  model: string;
  fingerprint: string;
  words: StyledWord[];
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

  // Hold a beat after the last word ends, then fade fully out so the pill
  // doesn't bleed into silent scenes.
  const lastEnd = window[window.length - 1].end;
  const opacity = interpolate(
    seconds,
    [lastEnd, lastEnd + 0.4, lastEnd + 1.0],
    [1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  if (opacity <= 0.001) return null;

  return <Pill opacity={opacity}>{buildLine(window)}</Pill>;
};

// ─── Phase G — Styled rolling window ───────────────────────────────────────
//
// When ``styled-captions-{variant}.json`` is present, Opus 4.7 has chosen a
// color, weight, animation, and emphasis_level for each word. We render the
// rolling 7-word window like dense mode but apply the per-word styling.

const STYLED_WINDOW_WORDS = 7;
const STYLED_FONT_SIZE_BASE = 56;
const STYLED_FONT_SIZE_LEVEL_2 = 64;
const STYLED_FONT_SIZE_LEVEL_3 = 72;

type StyledWordViewProps = {
  word: StyledWord;
  /** Seconds since composition start (uses the same clock as the segment timestamps). */
  seconds: number;
};

const StyledWordView = ({ word, seconds }: StyledWordViewProps) => {
  const localT = Math.max(0, seconds - word.start);
  const dur = Math.max(0.001, word.end - word.start);

  let opacity = 1;
  let transform = "";
  let textShadow = "0 4px 16px rgba(0,0,0,0.5)";

  switch (word.animation) {
    case "fade": {
      // Fade in over ~0.2s, hold, no special motion.
      opacity = interpolate(localT, [0, 0.2], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
      break;
    }
    case "pop": {
      const s = interpolate(
        localT,
        [0, 0.12, 0.24],
        [0.7, 1.18, 1],
        { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
      );
      transform = `scale(${s})`;
      break;
    }
    case "pulse": {
      // Cycles between 0.6 and 1.0 every ~0.6s while the word is on.
      const phase = ((localT % 0.6) / 0.6) * Math.PI * 2;
      opacity = 0.8 + Math.sin(phase) * 0.2;
      break;
    }
    case "scale": {
      // Subtle 1 → 1.15 → 1 over the word's duration.
      const peak = dur * 0.5;
      const s = interpolate(
        localT,
        [0, peak, dur],
        [1, 1.15, 1],
        { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
      );
      transform = `scale(${s})`;
      break;
    }
    case "glow": {
      const intensity = interpolate(
        localT,
        [0, 0.3, 0.6],
        [0, 1, 0.7],
        { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
      );
      const radius = 20 + intensity * 28;
      textShadow = `0 0 ${radius}px rgba(192,75,45,${0.55 + intensity * 0.4}), 0 4px 16px rgba(0,0,0,0.5)`;
      break;
    }
    default: {
      break;
    }
  }

  let fontSize = STYLED_FONT_SIZE_BASE;
  let label = word.word;
  if (word.emphasis_level === 3) {
    fontSize = STYLED_FONT_SIZE_LEVEL_3;
    label = word.word.toUpperCase();
  } else if (word.emphasis_level === 2) {
    fontSize = STYLED_FONT_SIZE_LEVEL_2;
  }

  const fontWeight =
    word.weight === "black" ? 900 : word.weight === "bold" ? 700 : 500;

  return (
    <span
      style={{
        color: word.color,
        fontWeight,
        fontSize,
        opacity,
        transform,
        textShadow,
        display: "inline-block",
        margin: "0 0.18em",
        lineHeight: 1.18,
        letterSpacing: "-0.005em",
        whiteSpace: "pre",
      }}
    >
      {label}
    </span>
  );
};

type StyledRollingWindowProps = {
  words: StyledWord[];
  fps: number;
};

const StyledRollingWindow = ({ words, fps }: StyledRollingWindowProps) => {
  const frame = useCurrentFrame();
  const seconds = frame / fps;

  let endIdx = -1;
  for (let i = 0; i < words.length; i++) {
    if (words[i].start <= seconds) {
      endIdx = i;
    } else {
      break;
    }
  }
  if (endIdx < 0) return null;

  // Anchor: walk back at most 7 words OR until a sentence break.
  let startIdx = Math.max(0, endIdx - STYLED_WINDOW_WORDS + 1);
  for (let i = endIdx - 1; i >= startIdx; i--) {
    if (/[.!?]$/.test(words[i].word.trim())) {
      startIdx = i + 1;
      break;
    }
  }

  const visible = words.slice(startIdx, endIdx + 1);
  if (visible.length === 0) return null;

  const lastEnd = visible[visible.length - 1].end;
  // Hold full opacity for 0.4s after last word, then fade out by 1.0s so the
  // pill doesn't bleed into silent scenes (cold open / wordmark).
  const containerOpacity = interpolate(
    seconds,
    [lastEnd, lastEnd + 0.4, lastEnd + 1.0],
    [1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  if (containerOpacity <= 0.001) return null;

  return (
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
        textAlign: "center",
        opacity: containerOpacity,
        pointerEvents: "none",
      }}
    >
      {visible.map((w, i) => (
        <StyledWordView
          key={`styled-${startIdx + i}-${w.start}`}
          word={w}
          seconds={seconds}
        />
      ))}
    </div>
  );
};

// For sparse variants A/B, the styled JSON groups words by segment_id so we
// only render windows whose first word has started. A whole segment's words
// share the same emphasis pop, so we render them as a styled pill.
type StyledSparseProps = {
  words: StyledWord[];
  fps: number;
};

const StyledSparseWindows = ({ words, fps }: StyledSparseProps) => {
  // Group by segment_id, preserving order.
  const groups = new Map<number, StyledWord[]>();
  for (const w of words) {
    const seg = w.segment_id;
    const existing = groups.get(seg);
    if (existing) {
      existing.push(w);
    } else {
      groups.set(seg, [w]);
    }
  }

  const segs = Array.from(groups.entries()).sort((a, b) => a[0] - b[0]);

  return (
    <>
      {segs.map(([segId, segWords]) => {
        const startSec = segWords[0].start;
        const endSec = segWords[segWords.length - 1].end;
        const startFrame = Math.max(0, Math.round(startSec * fps) - 2);
        const totalFrames = Math.max(
          24,
          Math.round((endSec - startSec + 2) * fps),
        );
        return (
          <Sequence
            key={`styled-seg-${segId}-${startSec}`}
            from={startFrame}
            durationInFrames={totalFrames}
          >
            <StyledRollingWindow words={segWords} fps={fps} />
          </Sequence>
        );
      })}
    </>
  );
};

// ─── Top-level component ───────────────────────────────────────────────────

type LoadedPayload =
  | { kind: "styled"; payload: StyledCaptionsPayload }
  | { kind: "plain"; payload: CaptionsPayload };

export type KineticCaptionsProps = {
  variant: CaptionsVariant;
  /** Optional pre-loaded plain payload — useful in tests / SSR. */
  payload?: CaptionsPayload;
};

const isStyledPayload = (data: unknown): data is StyledCaptionsPayload => {
  if (typeof data !== "object" || data === null) return false;
  const candidate = data as Record<string, unknown>;
  return (
    candidate.mode === "styled" &&
    Array.isArray(candidate.words) &&
    typeof candidate.variant === "string"
  );
};

export const KineticCaptions = ({
  variant,
  payload: providedPayload,
}: KineticCaptionsProps) => {
  const { fps } = useVideoConfig();
  const [loaded, setLoaded] = useState<LoadedPayload>({
    kind: "plain",
    payload: providedPayload ?? EMPTY_PAYLOAD,
  });

  useEffect(() => {
    if (providedPayload) {
      setLoaded({ kind: "plain", payload: providedPayload });
      return;
    }
    let cancelled = false;

    // Try the styled (Opus 4.7) JSON first; on any error, fall back to plain.
    const styledUrl = staticFile(`captions/styled-captions-${variant}.json`);
    const plainUrl = staticFile(`captions/captions-${variant}.json`);

    const loadPlain = () => {
      fetch(plainUrl)
        .then((r) => r.json() as Promise<CaptionsPayload>)
        .then((data) => {
          if (!cancelled) setLoaded({ kind: "plain", payload: data });
        })
        .catch(() => {
          // Captions are decorative; never crash the render on a bad fetch.
        });
    };

    fetch(styledUrl)
      .then((r) => {
        if (!r.ok) throw new Error(`styled HTTP ${r.status}`);
        return r.json() as Promise<unknown>;
      })
      .then((data) => {
        if (cancelled) return;
        if (isStyledPayload(data)) {
          setLoaded({ kind: "styled", payload: data });
        } else {
          loadPlain();
        }
      })
      .catch(() => {
        loadPlain();
      });

    return () => {
      cancelled = true;
    };
  }, [variant, providedPayload]);

  if (loaded.kind === "styled") {
    const { payload } = loaded;
    // Variant C is dense (continuous transcript) — render the rolling
    // window. Variants A and B are sparse — group by segment and render
    // each group inside its own Sequence.
    if (payload.variant === "C") {
      return (
        <AbsoluteFill style={{ pointerEvents: "none" }}>
          <StyledRollingWindow words={payload.words} fps={fps} />
        </AbsoluteFill>
      );
    }
    return (
      <AbsoluteFill style={{ pointerEvents: "none" }}>
        <StyledSparseWindows words={payload.words} fps={fps} />
      </AbsoluteFill>
    );
  }

  const { payload } = loaded;
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
