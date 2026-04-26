/**
 * ScenarioGrid — Scene 6 (v5.4 readability redesign)
 *
 * 2×2 grid layout — each tile fills ~40% width / ~35% height, big readable type.
 * All four tiles fade in over 0–60f. Each tile has a "focus pulse" beat that
 * matches VO timing, then all hold at full opacity for the final ~210f so the
 * viewer can re-read.
 *
 * Total runtime: 24s (720f).
 */
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

const CREAM = "rgb(245 240 230)";
const CREAM_CARD = "rgb(238 232 218)";
const SAGE = "rgb(148 176 136)";
const INK = "rgb(45 42 38)";
const INK_LIGHT = "rgb(110 105 96)";
const MONO = "ui-monospace, 'JetBrains Mono', monospace";
const SERIF = "Georgia, 'Times New Roman', serif";

interface TileData {
  icon: string;
  title: string;
  subtitle: string;
  body: string;
  stat: string;
  metaStat: string;
  color: string;
}

const TILES: TileData[] = [
  {
    icon: "🐄",
    title: "SICK COW",
    subtitle: "Cow A014 · pinkeye detected",
    body: "Agent flags pinkeye, drafts the vet packet, books the visit — all before sunrise.",
    stat: "VET PACKET DRAFTED · VISIT SCHEDULED",
    metaStat: "HerdHealthWatcher · 4s",
    color: SAGE,
  },
  {
    icon: "💧",
    title: "TANK LEAK",
    subtitle: "8 PSI overnight drop",
    body: "Drone inspects the trough, pinpoints the leak, logs GPS, pings the rancher with photo.",
    stat: "DRONE DISPATCHED · LEAK LOCATED",
    metaStat: "Trough 3 · south pasture · 6s",
    color: "rgb(120 180 220)",
  },
  {
    icon: "🐮",
    title: "CALVING",
    subtitle: "Cow #117 · 3:14 AM · labor pattern detected",
    body: "Priority page — not a maybe. Rancher notified immediately, dystocia watch active.",
    stat: "PRIORITY PAGE SENT",
    metaStat: "CalvingWatch · 3s",
    color: "rgb(210 178 138)",
  },
  {
    icon: "🌩",
    title: "HAILSTORM",
    subtitle: "45 min out · NWS radar confirmed",
    body: "Herd auto-rotates to shelter before the storm arrives — GrazingOptimizer re-routes paddocks.",
    stat: "PADDOCK B → SHELTER 2",
    metaStat: "Acoustic nudge sent · 5s",
    color: "rgb(180 160 120)",
  },
];

/** Per-tile focus beats (matches VO timing within the 720f scene). */
const FOCUS_BEATS: ReadonlyArray<readonly [number, number]> = [
  [90, 180],
  [200, 290],
  [310, 400],
  [420, 510],
] as const;

const ALL_FADE_IN_END = 60;       // all four tiles fully visible by 60f
const HOLD_START = 540;           // after final tile beat ends
const RESTING_OPACITY = 0.7;      // when not focused (still readable)

/** Larger SVG body visual for each scenario — scales up with the tile. */
function TileVisual({ tile, progress }: { tile: TileData; progress: number }) {
  const p = Math.min(1, Math.max(0, progress));
  const c = tile.color;
  const fade = interpolate(p, [0, 0.3], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const late = interpolate(p, [0.3, 0.85], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  if (tile.title === "SICK COW") {
    return (
      <svg width="320" height="80" viewBox="0 0 320 80" fill="none" style={{ opacity: fade }}>
        <ellipse cx="50" cy="44" rx="28" ry="18" fill={`${c}25`} stroke={c} strokeWidth="2" />
        <ellipse cx="26" cy="36" rx="11" ry="10" fill={`${c}25`} stroke={c} strokeWidth="1.8" />
        <circle cx="22" cy="34" r="4.5" fill="none" stroke="rgb(220 60 60)" strokeWidth="2" />
        <circle cx="22" cy="34" r="2" fill="rgb(220 60 60)" opacity={late} />
        <text x="92" y="32" fill={c} fontSize="15" fontFamily="monospace" opacity={fade}>83% confidence</text>
        <rect x="92" y="42" width="220" height="28" rx="6" fill={`${c}18`} stroke={c} strokeWidth="1.4" opacity={late} />
        <text x="102" y="61" fill={c} fontSize="13" fontWeight="700" fontFamily="monospace" opacity={late}>VET PACKET → SCHEDULED</text>
      </svg>
    );
  }
  if (tile.title === "TANK LEAK") {
    const barP = late;
    return (
      <svg width="320" height="80" viewBox="0 0 320 80" fill="none" style={{ opacity: fade }}>
        <rect x="6" y="6" width="120" height="70" rx="6" fill={`${c}12`} stroke={c} strokeWidth="1.6" />
        <text x="12" y="22" fill={c} fontSize="11" fontFamily="monospace">PSI</text>
        {[0.92, 0.82, 0.66, 0.46, 0.28, 0.14].map((h, i) => (
          <rect
            key={i}
            x={14 + i * 18}
            y={74 - h * 50 * Math.min(1, barP + i * 0.05)}
            width={14}
            height={h * 50 * Math.min(1, barP + i * 0.05)}
            rx="3"
            fill={c}
            opacity={0.55 + h * 0.3}
          />
        ))}
        <line x1="6" y1="74" x2="126" y2="74" stroke={c} strokeWidth="1" opacity="0.5" />
        <text x="142" y="32" fill={c} fontSize="15" fontFamily="monospace" opacity={fade}>8 → 2 PSI overnight</text>
        <text x="142" y="58" fill={c} fontSize="13" fontWeight="700" fontFamily="monospace" opacity={late}>DRONE → LEAK LOCATED</text>
      </svg>
    );
  }
  if (tile.title === "CALVING") {
    const buzzX = Math.sin(p * 40) * 2.5;
    return (
      <svg width="320" height="80" viewBox="0 0 320 80" fill="none" style={{ opacity: fade }}>
        <path d="M6 40 Q22 16 38 40 Q54 64 70 40 Q86 16 102 40 Q118 64 130 40" stroke={c} strokeWidth="2.5" fill="none" strokeLinecap="round" opacity={fade} />
        <text x="6" y="74" fill={c} fontSize="10" fontFamily="monospace" opacity="0.65">labor wave pattern</text>
        <g transform={`translate(${buzzX},0)`} opacity={late}>
          <rect x="148" y="12" width="38" height="60" rx="8" fill={`${c}20`} stroke={c} strokeWidth="2" />
          <line x1="158" y1="20" x2="176" y2="20" stroke={c} strokeWidth="2" strokeLinecap="round" />
          <circle cx="167" cy="64" r="3" fill={c} />
          <path d="M143 22 Q139 42 143 56" stroke={c} strokeWidth="1.4" fill="none" strokeLinecap="round" opacity="0.5" />
          <path d="M191 22 Q195 42 191 56" stroke={c} strokeWidth="1.4" fill="none" strokeLinecap="round" opacity="0.5" />
        </g>
        <text x="208" y="34" fill={c} fontSize="15" fontFamily="monospace" opacity={late}>3:14 AM</text>
        <text x="208" y="58" fill={c} fontSize="13" fontWeight="700" fontFamily="monospace" opacity={late}>PRIORITY PAGE</text>
      </svg>
    );
  }
  // HAILSTORM
  const rot = interpolate(late, [0, 1], [0, 300], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <svg width="320" height="80" viewBox="0 0 320 80" fill="none" style={{ opacity: fade }}>
      <ellipse cx="52" cy="40" rx="34" ry="22" fill={`${c}22`} stroke={c} strokeWidth="2" />
      <ellipse cx="34" cy="32" rx="14" ry="12" fill={`${c}22`} stroke={c} strokeWidth="1.6" />
      <ellipse cx="68" cy="34" rx="13" ry="11" fill={`${c}22`} stroke={c} strokeWidth="1.6" />
      <path d="M54 24 L46 40 L52 40 L42 60" stroke="rgb(220 180 40)" strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round" opacity={fade} />
      <g transform={`rotate(${rot},124,40)`}>
        <path d="M124 20 A20 20 0 1 1 104 40" stroke={c} strokeWidth="3" fill="none" strokeLinecap="round" opacity={late} />
        <polygon points="124,14 118,26 130,26" fill={c} opacity={late} />
      </g>
      <text x="160" y="34" fill={c} fontSize="15" fontFamily="monospace" opacity={late}>45 min out</text>
      <text x="160" y="58" fill={c} fontSize="13" fontWeight="700" fontFamily="monospace" opacity={late}>PADDOCK B → SHELTER 2</text>
    </svg>
  );
}

export const ScenarioGrid: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const titleOpacity = interpolate(frame, [0, 30], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const badgeOpacity = interpolate(frame, [60, 100], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  // Layout: 2×2 grid, ~40% W × ~35% H per tile, centred under the title.
  const TILE_W = Math.round(width * 0.40);
  const TILE_H = Math.round(height * 0.35);
  const GAP_X = Math.round(width * 0.03);
  const GAP_Y = Math.round(height * 0.04);
  const GRID_W = TILE_W * 2 + GAP_X;
  const GRID_LEFT = (width - GRID_W) / 2;
  const GRID_TOP = Math.round(height * 0.16); // leaves room for the title above

  const isHolding = frame >= HOLD_START;

  return (
    // backgroundColor at root — never inside opacity — eliminates gray flash
    <AbsoluteFill style={{ backgroundColor: CREAM }}>

      {/* Title */}
      <div style={{
        position: "absolute", top: 36, left: 0, right: 0, textAlign: "center",
        fontFamily: SERIF, fontWeight: 700, fontSize: 44, color: INK,
        letterSpacing: "-0.01em", opacity: titleOpacity,
      }}>
        Four Scenarios. Fully Automatic.
      </div>

      {/* Tiles — 2×2 grid */}
      {TILES.map((tile, i) => {
        const col = i % 2;
        const row = Math.floor(i / 2);
        const tileX = GRID_LEFT + col * (TILE_W + GAP_X);
        const tileY = GRID_TOP + row * (TILE_H + GAP_Y);

        // Per-tile staggered fade-in (over 0–60f). Each tile lags ~6f after the previous.
        const fadeInStart = i * 6;
        const fadeInEnd = fadeInStart + (ALL_FADE_IN_END - i * 6);
        const baseOpacity = interpolate(
          frame,
          [fadeInStart, fadeInEnd],
          [0, RESTING_OPACITY],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
        );

        // Focus pulse for this tile's beat.
        const [bStart, bEnd] = FOCUS_BEATS[i];
        const isFocusWindow = frame >= bStart && frame <= bEnd + 20;

        // Spring-driven focus envelope: rises 0→1 at bStart, falls back to 0 at bEnd.
        const focusUp = isFocusWindow
          ? spring({ frame: frame - bStart, fps, config: { damping: 80, stiffness: 180, mass: 0.8 } })
          : 0;
        const focusDown = frame > bEnd
          ? spring({ frame: frame - bEnd, fps, config: { damping: 90, stiffness: 200 } })
          : 0;
        const focusEnv = Math.max(0, focusUp - focusDown);

        // After the final beat, hold ALL tiles at full opacity for re-reading.
        const holdBoost = isHolding
          ? interpolate(frame, [HOLD_START, HOLD_START + 30], [0, 1 - RESTING_OPACITY], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            })
          : 0;

        const tileOpacity = Math.min(1, baseOpacity + focusEnv * (1 - RESTING_OPACITY) + holdBoost);
        const scale = 1 + focusEnv * 0.04; // subtle bump
        const borderW = 2 + focusEnv * 2;  // 2px → 4px

        // The "details" (subtitle, body, visual, stat) reveal during this tile's beat
        // and stay revealed through the final hold.
        const hasFiredBeat = frame >= bStart;
        const detailProgress = hasFiredBeat
          ? interpolate(frame, [bStart, bStart + 70], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
          : 0;

        return (
          <div
            key={tile.title}
            style={{
              position: "absolute",
              left: tileX,
              top: tileY,
              width: TILE_W,
              height: TILE_H,
              transform: `scale(${scale})`,
              transformOrigin: "center center",
              backgroundColor: CREAM_CARD,
              border: `${borderW}px solid ${tile.color}`,
              borderRadius: 22,
              padding: "26px 30px",
              display: "flex",
              flexDirection: "column",
              gap: 14,
              opacity: tileOpacity,
              overflow: "hidden",
              boxShadow:
                focusEnv > 0.05
                  ? `0 18px 60px rgba(0,0,0,${0.10 + focusEnv * 0.12}), 0 0 0 ${Math.round(focusEnv * 4)}px ${tile.color}30`
                  : "0 4px 14px rgba(0,0,0,0.08)",
            }}
          >
            {/* Header row: icon + title + subtitle */}
            <div style={{ display: "flex", alignItems: "flex-start", gap: 16 }}>
              <div style={{ fontSize: 52, lineHeight: 1 }}>{tile.icon}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    fontFamily: MONO,
                    fontWeight: 800,
                    fontSize: 30,
                    color: INK,
                    letterSpacing: "0.10em",
                    textTransform: "uppercase" as const,
                    lineHeight: 1.05,
                  }}
                >
                  {tile.title}
                </div>
                <div
                  style={{
                    fontFamily: MONO,
                    fontSize: 19,
                    color: tile.color,
                    marginTop: 6,
                    lineHeight: 1.25,
                    opacity: 0.4 + detailProgress * 0.6,
                  }}
                >
                  {tile.subtitle}
                </div>
              </div>
            </div>

            {/* Body sentence */}
            <div
              style={{
                fontFamily: SERIF,
                fontSize: 19,
                color: INK,
                lineHeight: 1.4,
                opacity: 0.35 + detailProgress * 0.65,
              }}
            >
              {tile.body}
            </div>

            {/* Dataviz glyph — reveals on this tile's beat */}
            <div
              style={{
                opacity: detailProgress,
                marginTop: "auto",
              }}
            >
              <TileVisual tile={tile} progress={detailProgress} />
            </div>

            {/* Stat row pinned to the bottom */}
            <div
              style={{
                borderTop: `1.5px solid ${tile.color}55`,
                paddingTop: 12,
                display: "flex",
                justifyContent: "space-between",
                alignItems: "baseline",
                gap: 12,
              }}
            >
              <div
                style={{
                  fontFamily: MONO,
                  fontSize: 17,
                  color: tile.color,
                  fontWeight: 700,
                  letterSpacing: "0.08em",
                  opacity: 0.4 + detailProgress * 0.6,
                }}
              >
                {tile.stat}
              </div>
              <div
                style={{
                  fontFamily: MONO,
                  fontSize: 13,
                  color: INK_LIGHT,
                  letterSpacing: "0.04em",
                  whiteSpace: "nowrap",
                  opacity: 0.5 + detailProgress * 0.5,
                }}
              >
                {tile.metaStat}
              </div>
            </div>
          </div>
        );
      })}

      {/* Opus badge */}
      <div style={{
        position: "absolute", bottom: 28, right: 44,
        fontFamily: MONO, fontSize: 12, color: INK_LIGHT, letterSpacing: "0.12em",
        textTransform: "uppercase" as const, opacity: badgeOpacity,
        padding: "6px 12px", border: `1px solid ${SAGE}60`, borderRadius: 6,
        backgroundColor: `${CREAM_CARD}cc`,
      }}>
        Powered by Opus 4.7 · 5-agent mesh
      </div>

      {/* Sub-label — appears once all 4 tiles have run their focus */}
      <div style={{
        position: "absolute", bottom: 28, left: 44,
        fontFamily: MONO, fontSize: 13, color: INK_LIGHT, letterSpacing: "0.10em",
        textTransform: "uppercase" as const,
        opacity: interpolate(frame, [540, 600], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
      }}>
        No rancher action needed
      </div>
    </AbsoluteFill>
  );
};
