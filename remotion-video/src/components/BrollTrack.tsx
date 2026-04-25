/**
 * BrollTrack — composites b-roll clips as a Z=1 overlay over dashboard footage.
 *
 * Driven by the broll-{A,B,C}.json track generated from OpenMontage EDLs.
 * Uses Series.Sequence for each cut so Remotion's timeline knows the exact
 * duration. OffthreadVideo handles the decode (required for server-side render).
 *
 * Z-stack contract:
 *   z=0  dashboard clips / ambient footage (act-level Video tags)
 *   z=1  THIS component — cinematic b-roll cutaways
 *   z=2+ text overlays, lower-thirds, anchor chips
 *
 * Opacity envelope: 8-frame ease in at the start of each cut,
 * 8-frame ease out at the end. Matches plan spec exactly.
 */
import {
  AbsoluteFill,
  OffthreadVideo,
  Series,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const FADE_FRAMES = 8;

// ── Types ─────────────────────────────────────────────────────────────────────

export type BrollCut = {
  startSeconds: number;
  endSeconds: number;
  src: string;
  transition: string;
  transitionDurationFrames: number;
  reason?: string;
};

type BrollClipProps = {
  cut: BrollCut;
};

// ── Per-clip inner component ──────────────────────────────────────────────────

const BrollClip = ({ cut }: BrollClipProps) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  // 8-frame opacity fade in at start, 8-frame fade out at end.
  const opacity = interpolate(
    frame,
    [0, FADE_FRAMES, durationInFrames - FADE_FRAMES, durationInFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  return (
    <AbsoluteFill
      style={{
        zIndex: 1,
        pointerEvents: "none",
      }}
    >
      <OffthreadVideo
        src={staticFile(cut.src)}
        muted
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          objectFit: "cover",
          opacity,
        }}
      />
    </AbsoluteFill>
  );
};

// ── BrollTrack props ──────────────────────────────────────────────────────────

type BrollTrackProps = {
  /** The parsed broll-{A,B,C}.json cuts array. */
  track: BrollCut[];
  /**
   * Global composition offset in seconds for this act.
   * E.g. ABAct1Hook passes 0; ABAct3Close passes its start second.
   * Clips whose startSeconds fall outside [offset, offset+actDuration] are
   * silently skipped — safe to pass the full track from any act.
   */
  compositionStartSeconds: number;
};

// ── BrollTrack root ───────────────────────────────────────────────────────────

export const BrollTrack = ({
  track,
  compositionStartSeconds,
}: BrollTrackProps) => {
  const { fps, durationInFrames } = useVideoConfig();
  const actDurationSeconds = durationInFrames / fps;

  // Build the Series.Sequence list from cuts that overlap this act window.
  const actStart = compositionStartSeconds;
  const actEnd = compositionStartSeconds + actDurationSeconds;

  // Filter to cuts that fall within this act's time window.
  const visibleCuts = track.filter(
    (cut) => cut.endSeconds > actStart && cut.startSeconds < actEnd,
  );

  if (visibleCuts.length === 0) {
    return null;
  }

  // Build the sequence list. Series expects sequential non-overlapping segments.
  // We fill gaps between cuts with empty placeholder segments so Series timing
  // stays aligned with the act's global clock.
  type Segment =
    | { kind: "cut"; cut: BrollCut; durationInFrames: number }
    | { kind: "gap"; durationInFrames: number };

  const segments: Segment[] = [];
  let cursorSeconds = actStart;

  for (const cut of visibleCuts) {
    const cutStart = Math.max(cut.startSeconds, actStart);
    const cutEnd = Math.min(cut.endSeconds, actEnd);

    // Gap before this cut
    if (cutStart > cursorSeconds) {
      const gapFrames = Math.round((cutStart - cursorSeconds) * fps);
      if (gapFrames > 0) {
        segments.push({ kind: "gap", durationInFrames: gapFrames });
      }
    }

    const cutFrames = Math.round((cutEnd - cutStart) * fps);
    if (cutFrames > 0) {
      segments.push({
        kind: "cut",
        cut,
        durationInFrames: cutFrames,
      });
    }

    cursorSeconds = cutEnd;
  }

  return (
    <AbsoluteFill
      style={{
        zIndex: 1,
        pointerEvents: "none",
        position: "absolute",
        inset: 0,
      }}
    >
      <Series>
        {segments.map((seg, i) => {
          if (seg.kind === "gap") {
            return (
              <Series.Sequence
                key={`gap-${i}`}
                durationInFrames={seg.durationInFrames}
                layout="none"
              >
                {/* empty — dashboard footage shows through */}
                <AbsoluteFill />
              </Series.Sequence>
            );
          }
          return (
            <Series.Sequence
              key={`cut-${i}-${seg.cut.src}`}
              durationInFrames={seg.durationInFrames}
              layout="none"
            >
              <BrollClip cut={seg.cut} />
            </Series.Sequence>
          );
        })}
      </Series>
    </AbsoluteFill>
  );
};
