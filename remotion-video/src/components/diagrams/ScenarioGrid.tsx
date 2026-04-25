/**
 * ScenarioGrid — Scene 6 (v5 Wave 2B rewrite)
 *
 * 4 scenario tiles, sequential focus (one fills ~45% viewport at a time).
 * Total runtime ~24s (720 frames). Fixes: cream bg frame-0, rich bodies, bigger stats.
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
    subtitle: "Cow A014 · 83% confidence",
    body: "Agent flags pinkeye, drafts vet packet, schedules the visit — all before sunrise",
    stat: "Agent acted in 4s",
    metaStat: "before sunrise · HerdHealthWatcher",
    color: SAGE,
  },
  {
    icon: "💧",
    title: "TANK LEAK",
    subtitle: "8 PSI overnight drop",
    body: "Drone inspects the leak, logs GPS coordinates, alerts rancher with photo",
    stat: "Agent acted in 6s",
    metaStat: "trough 3 · south pasture · drone path logged",
    color: "rgb(120 180 220)",
  },
  {
    icon: "🐮",
    title: "CALVING",
    subtitle: "Cow #117 · 3:14 AM · labor pattern detected",
    body: "Priority page — not a maybe. Rancher notified immediately, dystocia watch active",
    stat: "Agent acted in 3s",
    metaStat: "3:14 AM · CalvingWatch · priority page",
    color: "rgb(210 178 138)",
  },
  {
    icon: "🌩",
    title: "HAILSTORM",
    subtitle: "45 min out · NWS radar confirmed",
    body: "Herd auto-rotates to shelter before storm arrives — GrazingOptimizer re-routes",
    stat: "Agent acted in 5s",
    metaStat: "paddock B → shelter 2 · acoustic nudge sent",
    color: "rgb(180 160 120)",
  },
];

// v5.1 polish: tightened to fit 660f (22s) — 4 tiles
const FOCUS_DUR = 130;   // 4.33s per tile
const STAGGER  = 145;   // ~4.83s tile-to-tile
const TRANS   = 20;

/** Mini SVG body visual for each scenario */
function TileVisual({ tile, progress }: { tile: TileData; progress: number }) {
  const p = Math.min(1, Math.max(0, progress));
  const c = tile.color;
  const fade = interpolate(p, [0, 0.3], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const late = interpolate(p, [0.4, 0.85], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  if (tile.title === "SICK COW") {
    return (
      <svg width="220" height="56" viewBox="0 0 220 56" fill="none" style={{ opacity: fade }}>
        <ellipse cx="38" cy="32" rx="20" ry="13" fill={`${c}25`} stroke={c} strokeWidth="1.6" />
        <ellipse cx="20" cy="26" rx="8" ry="7" fill={`${c}25`} stroke={c} strokeWidth="1.4" />
        <circle cx="16" cy="24" r="3" fill="none" stroke="rgb(220 60 60)" strokeWidth="1.4" />
        <text x="68" y="22" fill={c} fontSize="11" fontFamily="monospace" opacity={fade}>Cow A014 · pinkeye detected</text>
        <rect x="68" y="30" width="140" height="18" rx="4" fill={`${c}18`} stroke={c} strokeWidth="1" opacity={late} />
        <text x="74" y="43" fill={c} fontSize="9" fontFamily="monospace" opacity={late}>VET PACKET DRAFTED · VISIT SCHEDULED</text>
      </svg>
    );
  }
  if (tile.title === "TANK LEAK") {
    const barP = late;
    return (
      <svg width="220" height="56" viewBox="0 0 220 56" fill="none" style={{ opacity: fade }}>
        <rect x="4" y="4" width="80" height="48" rx="4" fill={`${c}12`} stroke={c} strokeWidth="1.2" />
        <text x="8" y="16" fill={c} fontSize="8" fontFamily="monospace">PSI</text>
        {[0.9, 0.8, 0.65, 0.45, 0.28, 0.15].map((h, i) => (
          <rect key={i} x={8 + i * 12} y={52 - h * 36 * Math.min(1, barP + i * 0.05)} width={9} height={h * 36 * Math.min(1, barP + i * 0.05)} rx="2" fill={c} opacity={0.55 + h * 0.3} />
        ))}
        <line x1="4" y1="52" x2="84" y2="52" stroke={c} strokeWidth="0.8" opacity="0.5" />
        <text x="96" y="22" fill={c} fontSize="11" fontFamily="monospace" opacity={fade}>8 PSI → 2 PSI overnight</text>
        <text x="96" y="38" fill="rgb(60 160 230)" fontSize="9" fontFamily="monospace" opacity={late}>DRONE DISPATCHED · LEAK LOCATED</text>
      </svg>
    );
  }
  if (tile.title === "CALVING") {
    const buzzX = Math.sin(p * 40) * 2;
    return (
      <svg width="220" height="56" viewBox="0 0 220 56" fill="none" style={{ opacity: fade }}>
        <path d="M4 28 Q14 12 24 28 Q34 44 44 28 Q54 12 64 28 Q74 44 80 28" stroke={c} strokeWidth="2" fill="none" strokeLinecap="round" opacity={fade} />
        <text x="4" y="52" fill={c} fontSize="7" fontFamily="monospace" opacity="0.6">labor wave pattern</text>
        <g transform={`translate(${buzzX},0)`} opacity={late}>
          <rect x="96" y="8" width="28" height="44" rx="6" fill={`${c}20`} stroke={c} strokeWidth="1.6" />
          <line x1="104" y1="14" x2="116" y2="14" stroke={c} strokeWidth="1.6" strokeLinecap="round" />
          <circle cx="110" cy="46" r="2.5" fill={c} />
          <path d="M93 16 Q90 28 93 38" stroke={c} strokeWidth="1.2" fill="none" strokeLinecap="round" opacity="0.5" />
          <path d="M127 16 Q130 28 127 38" stroke={c} strokeWidth="1.2" fill="none" strokeLinecap="round" opacity="0.5" />
        </g>
        <text x="136" y="26" fill={c} fontSize="11" fontFamily="monospace" opacity={late}>3:14 AM</text>
        <text x="136" y="40" fill={c} fontSize="9" fontFamily="monospace" opacity={late}>PRIORITY PAGE SENT</text>
      </svg>
    );
  }
  // HAILSTORM
  const rot = interpolate(late, [0, 1], [0, 300], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <svg width="220" height="56" viewBox="0 0 220 56" fill="none" style={{ opacity: fade }}>
      <ellipse cx="36" cy="28" rx="24" ry="16" fill={`${c}22`} stroke={c} strokeWidth="1.6" />
      <ellipse cx="24" cy="22" rx="10" ry="9" fill={`${c}22`} stroke={c} strokeWidth="1.2" />
      <ellipse cx="48" cy="24" rx="9" ry="8" fill={`${c}22`} stroke={c} strokeWidth="1.2" />
      <path d="M38 18 L32 28 L36 28 L30 40" stroke="rgb(220 180 40)" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round" opacity={fade} />
      <g transform={`rotate(${rot},88,28)`}>
        <path d="M88 14 A14 14 0 1 1 74 28" stroke={c} strokeWidth="2.2" fill="none" strokeLinecap="round" opacity={late} />
        <polygon points="88,10 84,18 92,18" fill={c} opacity={late} />
      </g>
      <text x="116" y="24" fill={c} fontSize="11" fontFamily="monospace" opacity={late}>45 min out</text>
      <text x="116" y="38" fill={c} fontSize="9" fontFamily="monospace" opacity={late}>PADDOCK B → SHELTER 2</text>
    </svg>
  );
}

export const ScenarioGrid: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const badgeOpacity = interpolate(frame, [60, 100], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const ACTIVE_W = Math.round(width * 0.60);
  const ACTIVE_H = Math.round(height * 0.52);
  const MINI_W = Math.round(width * 0.13);
  const MINI_H = Math.round(height * 0.20);

  return (
    // backgroundColor at root — never inside opacity — eliminates gray flash
    <AbsoluteFill style={{ backgroundColor: CREAM }}>

      {/* Title */}
      <div style={{
        position: "absolute", top: 40, left: 0, right: 0, textAlign: "center",
        fontFamily: SERIF, fontWeight: 700, fontSize: 40, color: INK,
        letterSpacing: "-0.01em", opacity: titleOpacity,
      }}>
        Four Scenarios. Fully Automatic.
      </div>

      {/* Tiles */}
      {TILES.map((tile, i) => {
        const focusStart = i * STAGGER;
        const focusEnd = focusStart + FOCUS_DUR;
        const isFocused = frame >= focusStart && frame < focusEnd + TRANS;
        const isPast = frame > focusEnd + TRANS;
        const isVisible = frame >= focusStart - TRANS || i === 0;
        if (!isVisible) return null;

        const activeSp = spring({ frame: frame - focusStart, fps, config: { damping: 75, stiffness: 160, mass: 0.85 } });
        const exitSp = isPast ? spring({ frame: frame - focusEnd - TRANS, fps, config: { damping: 90, stiffness: 200 } }) : 0;

        const cW = isFocused ? interpolate(activeSp, [0, 1], [MINI_W, ACTIVE_W]) : MINI_W;
        const cH = isFocused ? interpolate(activeSp, [0, 1], [MINI_H, ACTIVE_H]) : MINI_H;

        const centX = (width - ACTIVE_W) / 2;
        const miniX = 36 + i * (MINI_W + 10);
        const cX = isFocused
          ? interpolate(activeSp, [0, 1], [miniX, centX])
          : isPast ? interpolate(exitSp, [0, 1], [centX, miniX]) : miniX;
        const cY = isFocused
          ? interpolate(activeSp, [0, 1], [(height - MINI_H) / 2, (height - ACTIVE_H) / 2 + 20])
          : (height - MINI_H) / 2;

        const cardOpacity = i === 0 && !isFocused && !isPast
          ? interpolate(frame, [0, 20], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
          : isFocused
          ? interpolate(activeSp, [0, 0.05, 1], [0, 0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
          : 0.55;

        const visualProg = isFocused
          ? interpolate(frame, [focusStart, focusStart + FOCUS_DUR], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
          : isPast ? 1 : 0;

        const statProg = isFocused
          ? interpolate(frame, [focusStart + 20, focusStart + 95], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
          : isPast ? 1 : 0;

        return (
          <div key={tile.title} style={{
            position: "absolute", left: cX, top: cY, width: cW, height: cH,
            backgroundColor: CREAM_CARD,
            border: `2.5px solid ${isFocused ? tile.color : `${tile.color}50`}`,
            borderRadius: 20, padding: isFocused ? "26px 30px" : "12px 14px",
            display: "flex", flexDirection: "column", justifyContent: "space-between",
            opacity: cardOpacity, overflow: "hidden",
            boxShadow: isFocused
              ? `0 16px 56px rgba(0,0,0,0.18), 0 0 0 3px ${tile.color}35`
              : "0 2px 8px rgba(0,0,0,0.06)",
          }}>
            {/* Header */}
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ fontSize: isFocused ? 44 : 22, lineHeight: 1 }}>{tile.icon}</div>
              <div>
                <div style={{ fontFamily: MONO, fontWeight: 800, fontSize: isFocused ? 22 : 12, color: INK, letterSpacing: "0.12em", textTransform: "uppercase" as const }}>
                  {tile.title}
                </div>
                {isFocused && (
                  <div style={{ fontFamily: MONO, fontSize: 13, color: tile.color, marginTop: 3,
                    opacity: interpolate(activeSp, [0.3, 0.7], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>
                    {tile.subtitle}
                  </div>
                )}
              </div>
            </div>

            {/* Sub-visual */}
            {isFocused && (
              <div style={{ opacity: interpolate(visualProg, [0, 0.3], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>
                <TileVisual tile={tile} progress={visualProg} />
              </div>
            )}

            {/* Body text */}
            {isFocused && (
              <div style={{ fontFamily: SERIF, fontSize: 21, color: INK, lineHeight: 1.4,
                opacity: interpolate(statProg, [0, 0.4], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>
                {tile.body}
              </div>
            )}

            {/* Stat row */}
            <div style={{ borderTop: `1.5px solid ${tile.color}40`, paddingTop: isFocused ? 14 : 7 }}>
              <div style={{ fontFamily: MONO, fontSize: isFocused ? 18 : 10, color: tile.color, fontWeight: 700, letterSpacing: "0.08em", opacity: statProg }}>
                {tile.stat}
              </div>
              {isFocused && (
                <div style={{ fontFamily: MONO, fontSize: 13, color: INK_LIGHT, marginTop: 4,
                  opacity: interpolate(statProg, [0.5, 1], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>
                  {tile.metaStat}
                </div>
              )}
            </div>
          </div>
        );
      })}

      {/* Opus badge */}
      <div style={{
        position: "absolute", bottom: 32, right: 48,
        fontFamily: MONO, fontSize: 12, color: INK_LIGHT, letterSpacing: "0.12em",
        textTransform: "uppercase" as const, opacity: badgeOpacity,
        padding: "6px 12px", border: `1px solid ${SAGE}60`, borderRadius: 6,
        backgroundColor: `${CREAM_CARD}cc`,
      }}>
        Powered by Opus 4.7 · 5-agent mesh
      </div>

      {/* Sub-label */}
      <div style={{
        position: "absolute", bottom: 32, left: 48,
        fontFamily: MONO, fontSize: 13, color: INK_LIGHT, letterSpacing: "0.10em",
        textTransform: "uppercase" as const,
        opacity: interpolate(frame, [540, 580], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
      }}>
        No rancher action needed
      </div>
    </AbsoluteFill>
  );
};
