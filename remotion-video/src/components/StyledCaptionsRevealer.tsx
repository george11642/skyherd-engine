/**
 * StyledCaptionsRevealer — meta-loop component for Phase 3.
 *
 * Shows a syntax-highlighted snippet of styled-captions-{variant}.json with
 * 3 cherry-picked high-impact words. Each word renders ABOVE the JSON in its
 * matching color/weight, connected by a thin sage line — visual proof the JSON
 * drives the video.
 *
 * Animation: monospace text types in left-to-right at ~30 chars/sec.
 * Background: warm cream rgb(248,244,234) with terminal-style top bar.
 *
 * Hard-coded cherry-picks per variant (cheap first pass per plan locked
 * decision; promote to live cross-reference only if iteration scoring demands).
 */
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { ACCENT_MAP } from "../acts/v2/shared";

export type StyledCaptionsRevealerProps = {
  variant: "A" | "B" | "C";
  /** Frame (within this Sequence's local timeline) at which typing begins. */
  appearFrame?: number;
};

// ─── Cherry-picked words per variant ─────────────────────────────────────────
// Selected for impact: highest emph_level words that are visually distinctive.

type CherryWord = {
  word: string;
  color: string;
  weight: number; // numeric CSS font-weight
  anim: string;
};

const CHERRY_PICKS: Record<"A" | "B" | "C", [CherryWord, CherryWord, CherryWord]> = {
  A: [
    { word: "don't.", color: "#C04B2D", weight: 900, anim: "pop" },
    { word: "need",   color: "#3D5A3D", weight: 700, anim: "pulse" },
    { word: "highs",  color: "#C04B2D", weight: 900, anim: "pop" },
  ],
  B: [
    { word: "$4.17",  color: "#C04B2D", weight: 900, anim: "pop" },
    { word: "ranch",  color: "#A36B3A", weight: 700, anim: "fade" },
    { word: "gone",   color: "#C04B2D", weight: 900, anim: "glow" },
  ],
  C: [
    { word: "Skyherd",  color: "#C04B2D", weight: 900, anim: "pop" },
    { word: "trough,",  color: "#A36B3A", weight: 700, anim: "fade" },
    { word: "watches",  color: "#3D5A3D", weight: 700, anim: "pulse" },
  ],
};

// Pad a string to a minimum length using spaces (avoids String.prototype.padEnd
// which requires lib: es2017+; this project targets es2015).
const pad = (s: string, len: number): string => {
  let result = s;
  while (result.length < len) result = result + " ";
  return result;
};

// Build the JSON snippet lines for display.
const buildLines = (variant: "A" | "B" | "C"): string[] => {
  const picks = CHERRY_PICKS[variant];
  return [
    `// styled-captions-${variant}.json · Opus 4.7 · 2026-04-24`,
    `{ "word": ${pad(JSON.stringify(picks[0].word), 12)}, "color": "${picks[0].color}", "weight": ${picks[0].weight}, "anim": "${picks[0].anim}" }`,
    `{ "word": ${pad(JSON.stringify(picks[1].word), 12)}, "color": "${picks[1].color}", "weight": ${picks[1].weight}, "anim": "${picks[1].anim}" }`,
    `{ "word": ${pad(JSON.stringify(picks[2].word), 12)}, "color": "${picks[2].color}", "weight": ${picks[2].weight}, "anim": "${picks[2].anim}" }`,
  ];
};

// Chars per second for the typewriter effect.
const CHARS_PER_SEC = 30;

// ─── Typewriter helper ────────────────────────────────────────────────────────

type TypewriterLineProps = {
  text: string;
  startFrame: number;
  fps: number;
  color?: string;
};

const TypewriterLine = ({ text, startFrame, fps, color }: TypewriterLineProps) => {
  const frame = useCurrentFrame();
  const localFrame = Math.max(0, frame - startFrame);
  const revealed = Math.floor((localFrame / fps) * CHARS_PER_SEC);
  const visible = text.slice(0, revealed);

  return (
    <span style={{ color: color ?? "rgb(72 84 76)" }}>
      {visible}
    </span>
  );
};

// ─── Main component ───────────────────────────────────────────────────────────

export const StyledCaptionsRevealer = ({
  variant,
  appearFrame = 0,
}: StyledCaptionsRevealerProps) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const picks = CHERRY_PICKS[variant];
  const lines = buildLines(variant);

  // Overall fade-in at appearFrame.
  const globalOpacity = interpolate(frame, [appearFrame, appearFrame + 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Stagger: comment line starts at appearFrame, then each JSON line after
  // the previous line finishes typing (approx).
  const commentChars = lines[0].length;
  const line0Start = appearFrame;
  const line1Start = line0Start + Math.ceil((commentChars / CHARS_PER_SEC) * fps) + 4;
  const line2Start = line1Start + Math.ceil((lines[1].length / CHARS_PER_SEC) * fps) + 4;
  const line3Start = line2Start + Math.ceil((lines[2].length / CHARS_PER_SEC) * fps) + 4;

  const lineStarts = [line0Start, line1Start, line2Start, line3Start];

  // Word "bubble" above JSON: each cherry-picked word appears when its JSON
  // line starts typing.
  const wordOpacity = (wordIdx: number): number => {
    const s = lineStarts[wordIdx + 1]; // offset by 1 (comment is line 0)
    return interpolate(frame, [s, s + 10], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  };

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        backgroundColor: "rgb(248 244 234)",
        opacity: globalOpacity,
        display: "flex",
        flexDirection: "column",
        fontFamily: "Inter, sans-serif",
      }}
    >
      {/* Terminal-style top bar */}
      <div
        style={{
          height: 44,
          backgroundColor: "rgb(230 224 210)",
          display: "flex",
          alignItems: "center",
          padding: "0 20px",
          gap: 10,
          borderBottom: "1px solid rgba(72,84,76,0.12)",
        }}
      >
        {/* Traffic light dots */}
        {["rgb(255 95 86)", "rgb(255 189 46)", "rgb(39 201 63)"].map((c, i) => (
          <div
            key={`dot-${i}`}
            style={{
              width: 14,
              height: 14,
              borderRadius: 7,
              backgroundColor: c,
            }}
          />
        ))}
        <div
          style={{
            flex: 1,
            textAlign: "center",
            fontSize: 14,
            color: "rgb(120 132 124)",
            fontWeight: 600,
            letterSpacing: "0.04em",
            fontFamily: "ui-monospace, JetBrains Mono, monospace",
          }}
        >
          {`styled-captions-${variant}.json`}
        </div>
      </div>

      {/* Content area */}
      <div style={{ flex: 1, display: "flex", padding: "60px 80px", gap: 80, alignItems: "center" }}>

        {/* Left: cherry-picked words with sage connectors */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 48,
            minWidth: 320,
            alignItems: "flex-start",
          }}
        >
          {picks.map((pick, i) => (
            <div
              key={`word-${i}`}
              style={{
                opacity: wordOpacity(i),
                display: "flex",
                flexDirection: "column",
                gap: 6,
              }}
            >
              {/* The styled word itself */}
              <div
                style={{
                  fontFamily: "Inter, sans-serif",
                  fontWeight: pick.weight,
                  fontSize: 52,
                  color: pick.color,
                  letterSpacing: "-0.02em",
                  lineHeight: 1,
                  textShadow: "0 2px 12px rgba(0,0,0,0.08)",
                }}
              >
                {pick.word}
              </div>
              {/* Thin sage connector line */}
              <div
                style={{
                  width: 3,
                  height: 24,
                  backgroundColor: ACCENT_MAP.sage,
                  borderRadius: 2,
                  marginLeft: 8,
                  opacity: 0.7,
                }}
              />
              {/* Anim label */}
              <div
                style={{
                  fontFamily: "ui-monospace, JetBrains Mono, monospace",
                  fontSize: 13,
                  color: "rgb(120 132 124)",
                  letterSpacing: "0.08em",
                  marginLeft: 8,
                }}
              >
                anim: {pick.anim}
              </div>
            </div>
          ))}
        </div>

        {/* Right: syntax-highlighted JSON snippet */}
        <div
          style={{
            flex: 1,
            backgroundColor: "rgb(38 42 48)",
            borderRadius: 14,
            padding: "32px 36px",
            fontFamily: "ui-monospace, JetBrains Mono, Cascadia Code, monospace",
            fontSize: 22,
            lineHeight: 1.75,
            boxShadow: "0 12px 48px rgba(0,0,0,0.18)",
            overflow: "hidden",
          }}
        >
          {/* Comment line */}
          <div style={{ marginBottom: 8 }}>
            <TypewriterLine
              text={lines[0]}
              startFrame={lineStarts[0]}
              fps={fps}
              color="rgb(104 124 110)"
            />
          </div>

          {/* Three JSON lines — each with per-token coloring */}
          {[0, 1, 2].map((i) => {
            const pick = picks[i];
            const rawLine = lines[i + 1];
            return (
              <div key={`json-line-${i}`} style={{ marginBottom: 4 }}>
                <TypewriterLine
                  text={rawLine}
                  startFrame={lineStarts[i + 1]}
                  fps={fps}
                  color={pick.color}
                />
              </div>
            );
          })}
        </div>

      </div>

      {/* Bottom label */}
      <div
        style={{
          padding: "0 80px 36px",
          fontFamily: "ui-monospace, JetBrains Mono, monospace",
          fontSize: 14,
          color: ACCENT_MAP.sage,
          letterSpacing: "0.18em",
          textTransform: "uppercase",
          fontWeight: 700,
          opacity: interpolate(frame, [appearFrame + 20, appearFrame + 40], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        Opus 4.7 authored every color · weight · animation in this video
      </div>
    </div>
  );
};
