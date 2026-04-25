/**
 * SoftwareMVPBlocks — Scene 7 (v5 Wave 2B rewrite)
 *
 * 5-card grid: WEB DASHBOARD / iOS APP / ANDROID APP / SIMULATOR / VOICE-AI RANCHER
 * Cards fade in sequentially over ~12s (2.4s × 5). Sub-line types in after.
 * Total runtime ~22s (660 frames). Fixes: rich bodies, Wes phone card, +50% sub-line.
 */
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

const CREAM_CARD = "rgb(238 232 218)";
const CREAM_BG = "rgb(228 220 205)";
const SAGE = "rgb(148 176 136)";
const TERRACOTTA = "rgb(188 90 60)";
const INK = "rgb(45 42 38)";
const INK_LIGHT = "rgb(110 105 96)";
const MONO = "ui-monospace, 'JetBrains Mono', monospace";
const SERIF = "Georgia, 'Times New Roman', serif";

// ─── Card body sub-visuals ───────────────────────────────────────────────────

function WebBody({ accent, lf }: { accent: string; lf: number }) {
  const p = interpolate(lf, [20, 110], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const bars = [0.55, 0.82, 0.48, 0.93, 0.70, 0.86, 0.62];
  return (
    <svg width="100%" height="88" viewBox="0 0 200 88" fill="none">
      <rect x="0" y="0" width="200" height="88" rx="6" fill={`${accent}12`} stroke={accent} strokeWidth="1.4" />
      <rect x="0" y="0" width="200" height="17" rx="6" fill={`${accent}22`} />
      <circle cx="10" cy="8.5" r="2.8" fill={`${accent}60`} /><circle cx="19" cy="8.5" r="2.8" fill={`${accent}60`} /><circle cx="28" cy="8.5" r="2.8" fill={`${accent}60`} />
      <rect x="36" y="4" width="110" height="9" rx="3" fill={`${accent}25`} />
      <text x="40" y="12" fill={accent} fontSize="6.5" fontFamily="monospace" opacity="0.85">skyherd · live dashboard</text>
      {bars.map((h, i) => {
        const bh = h * 46 * p;
        return <rect key={i} x={6 + i * 27} y={80 - bh} width={19} height={bh} rx="2" fill={accent} opacity={0.5 + h * 0.35} />;
      })}
      <line x1="4" y1="80" x2="196" y2="80" stroke={accent} strokeWidth="0.7" opacity="0.4" />
      <text x="4" y="87" fill={accent} fontSize="5.5" fontFamily="monospace" opacity="0.55">events · 7-day window</text>
    </svg>
  );
}

function IOSBody({ accent, lf }: { accent: string; lf: number }) {
  const p = interpolate(lf, [50, 120], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div style={{ display: "flex", justifyContent: "center", height: 88 }}>
      <svg width="58" height="88" viewBox="0 0 58 88" fill="none">
        <rect x="4" y="0" width="50" height="88" rx="10" fill={`${accent}15`} stroke={accent} strokeWidth="1.8" />
        <line x1="18" y1="5" x2="40" y2="5" stroke={accent} strokeWidth="2" strokeLinecap="round" />
        <circle cx="29" cy="82" r="3.5" fill={`${accent}70`} stroke={accent} strokeWidth="1" />
        <rect x="8" y="12" width="42" height="66" rx="4" fill={`${accent}10`} opacity={p} />
        <rect x="10" y="18" width="38" height="14" rx="3" fill={`${accent}35`} opacity={p} />
        <text x="14" y="28" fill={accent} fontSize="6" fontFamily="monospace" opacity={p * 0.9}>⚠ COW A014</text>
        <rect x="10" y="36" width="28" height="5" rx="2" fill={`${accent}25`} opacity={p} />
        <rect x="10" y="44" width="20" height="5" rx="2" fill={`${accent}18`} opacity={p} />
        <rect x="11" y="56" width="36" height="12" rx="4" fill={accent} opacity={p * 0.85} />
        <text x="18" y="65" fill="white" fontSize="6" fontFamily="monospace" opacity={p}>VIEW ALERT</text>
      </svg>
    </div>
  );
}

function AndroidBody({ accent, lf }: { accent: string; lf: number }) {
  const p = interpolate(lf, [70, 140], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div style={{ display: "flex", justifyContent: "center", height: 88 }}>
      <svg width="60" height="88" viewBox="0 0 60 88" fill="none">
        <path d="M8 22 Q8 8 30 8 Q52 8 52 22 L52 76 Q52 84 44 84 L16 84 Q8 84 8 76 Z" fill={`${accent}15`} stroke={accent} strokeWidth="1.8" />
        <circle cx="20" cy="17" r="2.5" fill={accent} opacity="0.7" /><circle cx="40" cy="17" r="2.5" fill={accent} opacity="0.7" />
        <line x1="8" y1="26" x2="4" y2="26" stroke={accent} strokeWidth="2.2" strokeLinecap="round" />
        <line x1="52" y1="26" x2="56" y2="26" stroke={accent} strokeWidth="2.2" strokeLinecap="round" />
        <line x1="20" y1="84" x2="20" y2="88" stroke={accent} strokeWidth="2" strokeLinecap="round" />
        <line x1="40" y1="84" x2="40" y2="88" stroke={accent} strokeWidth="2" strokeLinecap="round" />
        <line x1="14" y1="5" x2="18" y2="13" stroke={accent} strokeWidth="1.5" strokeLinecap="round" />
        <line x1="46" y1="5" x2="42" y2="13" stroke={accent} strokeWidth="1.5" strokeLinecap="round" />
        <rect x="11" y="30" width="38" height="22" rx="4" fill={`${accent}28`} opacity={p} />
        <text x="14" y="41" fill={accent} fontSize="6" fontFamily="monospace" opacity={p}>SkyHerd Alert</text>
        <text x="14" y="49" fill={INK_LIGHT} fontSize="5.5" fontFamily="monospace" opacity={p * 0.85}>Trough 3 pressure low</text>
      </svg>
    </div>
  );
}

function SimBody({ accent, lf }: { accent: string; lf: number }) {
  const lines = ["$ make demo SEED=42", "→ FenceLineDispatcher", "→ confidence: 91%", "✓ drone dispatched", "✓ rancher paged", "→ scenario: calving", "✓ replay complete"];
  const visible = Math.ceil(interpolate(lf, [10, 160], [0, lines.length], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  return (
    <svg width="100%" height="88" viewBox="0 0 200 88" fill="none">
      <rect x="0" y="0" width="200" height="88" rx="6" fill="rgb(18 22 28)" />
      <rect x="0" y="0" width="200" height="16" rx="6" fill="rgb(32 38 48)" />
      <circle cx="10" cy="8" r="2.8" fill="rgb(255 90 90)" /><circle cx="19" cy="8" r="2.8" fill="rgb(255 200 50)" /><circle cx="28" cy="8" r="2.8" fill="rgb(80 200 100)" />
      <text x="36" y="12" fill="rgb(100 120 145)" fontSize="6.5" fontFamily="monospace">terminal</text>
      {lines.slice(0, visible).map((l, i) => (
        <text key={i} x="6" y={24 + i * 9} fill={l.startsWith("$") ? accent : l.startsWith("✓") ? "rgb(80 200 100)" : "rgb(175 192 210)"} fontSize="7" fontFamily="monospace">{l}</text>
      ))}
      <rect x={6 + (lines[Math.max(0, visible - 1)]?.length ?? 0) * 4.1} y={15 + Math.max(0, visible - 1) * 9} width="5" height="7" fill={accent} opacity={(Math.floor(lf / 10) % 2 === 0) ? 0.9 : 0} />
    </svg>
  );
}

function WesBody({ accent, lf }: { accent: string; lf: number }) {
  const p = interpolate(lf, [30, 100], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const ring1 = (lf % 50) / 50;
  const ring2 = ((lf + 25) % 50) / 50;
  return (
    <div style={{ display: "flex", justifyContent: "center", height: 88 }}>
      <svg width="62" height="88" viewBox="0 0 62 88" fill="none">
        <rect x="3" y="0" width="56" height="88" rx="11" fill="rgb(18 18 22)" stroke={accent} strokeWidth="1.8" />
        <line x1="19" y1="5" x2="43" y2="5" stroke={accent} strokeWidth="1.8" strokeLinecap="round" opacity="0.6" />
        <circle cx="31" cy="83" r="3.2" fill="rgb(36 36 44)" stroke={accent} strokeWidth="0.9" />
        <rect x="7" y="10" width="48" height="70" rx="7" fill="rgb(12 12 16)" opacity={p} />
        <text x="31" y="22" fill="rgb(150 160 180)" fontSize="5.5" fontFamily="sans-serif" textAnchor="middle" opacity={p * 0.9}>incoming call</text>
        <circle cx="31" cy="42" r={12 * (1 + ring1 * 0.42)} fill="none" stroke={accent} strokeWidth="0.9" opacity={Math.max(0, (1 - ring1) * 0.5 * p)} />
        <circle cx="31" cy="42" r={12 * (1 + ring2 * 0.42)} fill="none" stroke={accent} strokeWidth="0.9" opacity={Math.max(0, (1 - ring2) * 0.5 * p)} />
        <circle cx="31" cy="42" r="12" fill={`${accent}32`} stroke={accent} strokeWidth="1.4" opacity={p} />
        <path d="M23 44 Q23 38 31 38 Q39 38 39 44 L37 46 L25 46 Z" fill={accent} opacity={p * 0.85} />
        <rect x="21" y="45" width="20" height="3" rx="1.5" fill={accent} opacity={p * 0.75} />
        <text x="31" y="59" fill="white" fontSize="7.5" fontFamily="sans-serif" textAnchor="middle" fontWeight="bold" opacity={p}>Wes</text>
        <text x="31" y="67" fill={accent} fontSize="5.2" fontFamily="monospace" textAnchor="middle" opacity={p * 0.85}>SkyHerd · Twilio</text>
        <circle cx="19" cy="77" r="7" fill="rgb(215 48 48)" opacity={p * 0.9} />
        <circle cx="43" cy="77" r="7" fill="rgb(48 178 78)" opacity={p * 0.9} />
        <text x="19" y="80.5" fill="white" fontSize="8" textAnchor="middle" opacity={p}>✕</text>
        <text x="43" y="80.5" fill="white" fontSize="7" textAnchor="middle" opacity={p}>✓</text>
      </svg>
    </div>
  );
}

// ─── Card definitions ────────────────────────────────────────────────────────

interface CardDef {
  label: string;
  caption: string;
  color: string;
  appearFrame: number;
  Body: React.FC<{ accent: string; lf: number }>;
}

const CARDS: CardDef[] = [
  { label: "WEB DASHBOARD",    caption: "FastAPI + React 19 + Tailwind",      color: SAGE,                  appearFrame: 10,  Body: WebBody     },
  { label: "iOS APP",          caption: "SwiftUI · iPhone PWA",               color: "rgb(120 180 220)",    appearFrame: 72,  Body: IOSBody     },
  { label: "ANDROID APP",      caption: "React Native · Rancher PWA",         color: TERRACOTTA,            appearFrame: 144, Body: AndroidBody },
  { label: "SIMULATOR",        caption: "make demo SEED=42 · deterministic",  color: "rgb(210 178 138)",    appearFrame: 216, Body: SimBody     },
  { label: "VOICE-AI RANCHER", caption: "Wes · Twilio · ElevenLabs",         color: "rgb(188 140 200)",    appearFrame: 288, Body: WesBody     },
];

const SUBLINE = "Open source · MIT licensed · 1106 tests · 87% coverage · Voice-AI rancher persona over Twilio";
const TW_START = 360;
const TW_END = 580;

export const SoftwareMVPBlocks: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  // 5-card grid: 3 top + 2 bottom (centred)
  const GAP = 18;
  const cardW = Math.min(Math.floor((width - GAP * 4) / 3), 336);
  const cardH = Math.min(Math.floor((height - 270) / 2), 218);
  const topW = 3 * cardW + 2 * GAP;
  const botW = 2 * cardW + GAP;
  const topX = (width - topW) / 2;
  const botX = (width - botW) / 2;
  const rowY0 = 118;
  const rowY1 = rowY0 + cardH + GAP;

  function pos(i: number) {
    if (i < 3) return { x: topX + i * (cardW + GAP), y: rowY0 };
    return { x: botX + (i - 3) * (cardW + GAP), y: rowY1 };
  }

  const typeP = interpolate(frame, [TW_START, TW_END], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const visText = SUBLINE.slice(0, Math.floor(typeP * SUBLINE.length));

  return (
    // bg at root, never inside opacity — no gray flash
    <AbsoluteFill style={{ backgroundColor: CREAM_BG }}>

      <div style={{
        position: "absolute", top: 38, left: 0, right: 0, textAlign: "center",
        fontFamily: SERIF, fontWeight: 700, fontSize: 38, color: INK,
        letterSpacing: "-0.01em", opacity: titleOpacity,
      }}>
        Full Software MVP — Built Solo
      </div>

      {CARDS.map((card, i) => {
        const p = pos(i);
        const sp = spring({ frame: frame - card.appearFrame, fps, config: { damping: 110, stiffness: 155, mass: 0.75 } });
        const scaleVal = interpolate(sp, [0, 1], [0.84, 1]);
        const opacityVal = interpolate(sp, [0, 0.05, 1], [0, 0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        const pulsePhase = frame > 350 ? ((frame - 350 - i * 15) % (fps * 3.5)) : 999;
        const glow = pulsePhase < 22 ? interpolate(pulsePhase, [0, 11, 22], [0, 0.6, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 0;
        const lf = Math.max(0, frame - card.appearFrame);

        return (
          <div key={card.label} style={{
            position: "absolute", left: p.x, top: p.y, width: cardW, height: cardH,
            backgroundColor: CREAM_CARD, border: `2px solid ${card.color}`,
            borderRadius: 18, padding: "16px 18px",
            display: "flex", flexDirection: "column", justifyContent: "space-between",
            transform: `scale(${scaleVal})`, opacity: opacityVal, transformOrigin: "center center",
            overflow: "hidden",
            boxShadow: `0 4px 20px rgba(0,0,0,0.10)${glow > 0 ? `, 0 0 ${Math.round(22 * glow)}px ${card.color}` : ""}`,
          }}>
            <div style={{ fontFamily: MONO, fontWeight: 800, fontSize: 13, color: INK, letterSpacing: "0.12em", textTransform: "uppercase" as const, marginBottom: 6 }}>
              {card.label}
            </div>

            <div style={{ flex: 1, display: "flex", alignItems: "center" }}>
              <div style={{ width: "100%" }}>
                <card.Body accent={card.color} lf={lf} />
              </div>
            </div>

            <div style={{ fontFamily: MONO, fontSize: 11, color: card.color, letterSpacing: "0.07em", borderTop: `1px solid ${card.color}40`, paddingTop: 7, marginTop: 5 }}>
              {card.caption}
            </div>
          </div>
        );
      })}

      {/* Typewriter sub-line — 21px = +50% vs old 14px */}
      <div style={{
        position: "absolute", bottom: 34,
        left: topX, right: topX,
        fontFamily: MONO, fontSize: 21, color: INK_LIGHT,
        letterSpacing: "0.04em", lineHeight: 1.5, minHeight: 58,
      }}>
        {visText}
        {typeP < 1 && frame > TW_START && (
          <span style={{
            display: "inline-block", width: 2, height: "1em",
            backgroundColor: SAGE, marginLeft: 2, verticalAlign: "text-bottom",
            opacity: Math.floor(frame / 8) % 2 === 0 ? 1 : 0,
          }} />
        )}
      </div>
    </AbsoluteFill>
  );
};
