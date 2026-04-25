/**
 * ScenarioGrid — Scene 1:32–1:50 (18s / 540 frames @ 30fps)
 *
 * 2×2 grid of scenario tiles. Each tile gets ~4s of focus (sequential).
 * Tile slides in, content fades, stat counter animates, then tile dims for next.
 */
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

const CREAM = "rgb(245 240 230)";
const CREAM_CARD = "rgb(238 232 218)";
const SAGE = "rgb(148 176 136)";
const INK = "rgb(45 42 38)";
const INK_LIGHT = "rgb(110 105 96)";
const MONO = "ui-monospace, 'JetBrains Mono', monospace";
const SERIF = "Georgia, 'Times New Roman', serif";

interface Tile {
  icon: string;
  title: string;
  body: string;
  stat: string;
  accentColor: string;
}

const TILES: Tile[] = [
  {
    icon: "🐄",
    title: "SICK COW",
    body: "Vet packet sent before sunrise",
    stat: "83% confidence · A014",
    accentColor: SAGE,
  },
  {
    icon: "💧",
    title: "TANK LEAK",
    body: "Drone flies the leak",
    stat: "8 PSI overnight drop",
    accentColor: "rgb(120 180 220)",
  },
  {
    icon: "🤰",
    title: "CALVING",
    body: "Priority page sent immediately",
    stat: "Cow #117 · 3:14 AM",
    accentColor: "rgb(210 178 138)",
  },
  {
    icon: "🌩",
    title: "STORM",
    body: "Herd auto-rotates to shelter",
    stat: "45 min · Paddock B → Shelter 2",
    accentColor: "rgb(180 160 120)",
  },
];

// Each tile is "active" for ~4s (120 frames), staggered
const TILE_FOCUS_DUR = 110;
const TILE_STAGGER = 115;
const ALL_IN = 10; // All tiles visible after 10 frames

export const ScenarioGrid: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const fadeIn = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const cardW = Math.min((width - 160) / 2, 500);
  const cardH = Math.min((height - 240) / 2, 260);
  const gridX = (width - cardW * 2 - 32) / 2;
  const gridY = 160;

  const positions = [
    { col: 0, row: 0 },
    { col: 1, row: 0 },
    { col: 0, row: 1 },
    { col: 1, row: 1 },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: CREAM, opacity: fadeIn }}>
      {/* Title */}
      <div
        style={{
          position: "absolute",
          top: 48,
          left: 0,
          right: 0,
          textAlign: "center",
          fontFamily: SERIF,
          fontWeight: 700,
          fontSize: 36,
          color: INK,
          letterSpacing: "-0.01em",
        }}
      >
        Four More Scenarios Covered
      </div>

      {/* Tiles */}
      {TILES.map((tile, i) => {
        const pos = positions[i];
        const focusStart = i * TILE_STAGGER;
        const focusEnd = focusStart + TILE_FOCUS_DUR;
        const isFocused = frame >= focusStart && frame <= focusEnd;

        // Slide in
        const slideDir = pos.col === 0 ? -1 : 1;
        const sp = spring({
          frame: frame - focusStart + ALL_IN,
          fps,
          config: { damping: 110, stiffness: 160, mass: 0.8 },
        });
        const slideX = interpolate(sp, [0, 1], [slideDir * 60, 0]);
        const cardOpacity = interpolate(sp, [0, 0.05, 1], [0, 0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });

        // Dim inactive (after focus window)
        const dimOpacity = frame > focusEnd + 30
          ? interpolate(frame, [focusEnd + 30, focusEnd + 60], [1, 0.45], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            })
          : 1;

        // Stat counter: counts up during focus window
        const statProgress = isFocused
          ? interpolate(frame, [focusStart + 20, focusStart + 80], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            })
          : frame > focusEnd ? 1 : 0;

        const left = gridX + pos.col * (cardW + 32) + slideX;
        const top = gridY + pos.row * (cardH + 28);

        return (
          <div
            key={tile.title}
            style={{
              position: "absolute",
              left,
              top,
              width: cardW,
              height: cardH,
              backgroundColor: CREAM_CARD,
              border: `2px solid ${isFocused ? tile.accentColor : "rgba(148,176,136,0.3)"}`,
              borderRadius: 16,
              padding: 28,
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
              opacity: cardOpacity * dimOpacity,
              boxShadow: isFocused
                ? `0 8px 32px rgba(0,0,0,0.14), 0 0 0 2px ${tile.accentColor}`
                : "0 2px 8px rgba(0,0,0,0.06)",
            }}
          >
            {/* Icon + title */}
            <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
              <div style={{ fontSize: 42, lineHeight: 1 }}>{tile.icon}</div>
              <div
                style={{
                  fontFamily: MONO,
                  fontWeight: 800,
                  fontSize: 18,
                  color: INK,
                  letterSpacing: "0.14em",
                  textTransform: "uppercase",
                }}
              >
                {tile.title}
              </div>
            </div>

            {/* Body */}
            <div
              style={{
                fontFamily: SERIF,
                fontSize: 20,
                color: INK,
                lineHeight: 1.35,
                opacity: interpolate(statProgress, [0, 0.3], [0, 1], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                }),
              }}
            >
              {tile.body}
            </div>

            {/* Stat callout */}
            <div
              style={{
                fontFamily: MONO,
                fontSize: 13,
                color: tile.accentColor,
                fontWeight: 700,
                letterSpacing: "0.08em",
                borderTop: `1px solid ${tile.accentColor}40`,
                paddingTop: 10,
                opacity: interpolate(statProgress, [0.5, 1], [0, 1], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                }),
              }}
            >
              {tile.stat}
            </div>
          </div>
        );
      })}

      {/* Sub label */}
      <div
        style={{
          position: "absolute",
          bottom: 36,
          left: 0,
          right: 0,
          textAlign: "center",
          fontFamily: MONO,
          fontSize: 14,
          color: INK_LIGHT,
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          opacity: interpolate(frame, [380, 420], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        All handled automatically · No rancher action needed
      </div>
    </AbsoluteFill>
  );
};
