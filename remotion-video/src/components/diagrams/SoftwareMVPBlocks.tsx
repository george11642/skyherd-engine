/**
 * SoftwareMVPBlocks — Scene 1:50–2:10 (20s / 600 frames @ 30fps)
 *
 * 4 cards fade in sequentially over ~8s, then typewriter sub-line runs.
 * Cards: WEB DASHBOARD · iOS APP · ANDROID APP · DETERMINISTIC SIMULATOR
 */
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

const CREAM_CARD = "rgb(238 232 218)";
const CREAM_BG = "rgb(228 220 205)";
const SAGE = "rgb(148 176 136)";
const TERRACOTTA = "rgb(188 90 60)";
const INK = "rgb(45 42 38)";
const INK_LIGHT = "rgb(110 105 96)";
const MONO = "ui-monospace, 'JetBrains Mono', monospace";

interface Card {
  label: string;
  caption: string;
  icon: React.ReactNode;
  accentColor: string;
  appearFrame: number;
}

// Typewriter sub-line
const SUBLINE = "Voice-AI rancher persona over Twilio · Open source · MIT-licensed · 1106 tests · 87% coverage";
const TYPEWRITER_START = 240;
const TYPEWRITER_END = 480;

// Phone outline SVG
const PhoneIcon = ({ color }: { color: string }) => (
  <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
    <rect x="10" y="4" width="28" height="40" rx="5" stroke={color} strokeWidth="2.5" fill="none" />
    <circle cx="24" cy="40" r="2" fill={color} />
    <line x1="18" y1="9" x2="30" y2="9" stroke={color} strokeWidth="2" strokeLinecap="round" />
  </svg>
);

// Browser frame SVG
const BrowserIcon = ({ color }: { color: string }) => (
  <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
    <rect x="4" y="8" width="40" height="32" rx="4" stroke={color} strokeWidth="2.5" fill="none" />
    <line x1="4" y1="18" x2="44" y2="18" stroke={color} strokeWidth="2" />
    <circle cx="11" cy="13" r="2" fill={color} />
    <circle cx="18" cy="13" r="2" fill={color} />
    <circle cx="25" cy="13" r="2" fill={color} />
  </svg>
);

// Terminal icon SVG
const TerminalIcon = ({ color }: { color: string }) => (
  <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
    <rect x="4" y="8" width="40" height="32" rx="4" stroke={color} strokeWidth="2.5" fill="none" />
    <polyline points="12,20 20,26 12,32" stroke={color} strokeWidth="2.5" fill="none" strokeLinejoin="round" strokeLinecap="round" />
    <line x1="22" y1="32" x2="36" y2="32" stroke={color} strokeWidth="2" strokeLinecap="round" />
  </svg>
);

// Android outline SVG (head + body simplified)
const AndroidIcon = ({ color }: { color: string }) => (
  <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
    <path d="M14 20 Q14 10 24 10 Q34 10 34 20 L34 36 Q34 40 30 40 L18 40 Q14 40 14 36 Z" stroke={color} strokeWidth="2.5" fill="none" />
    <circle cx="19" cy="18" r="2" fill={color} />
    <circle cx="29" cy="18" r="2" fill={color} />
    <line x1="10" y1="24" x2="14" y2="24" stroke={color} strokeWidth="2.5" strokeLinecap="round" />
    <line x1="34" y1="24" x2="38" y2="24" stroke={color} strokeWidth="2.5" strokeLinecap="round" />
    <line x1="19" y1="40" x2="19" y2="44" stroke={color} strokeWidth="2.5" strokeLinecap="round" />
    <line x1="29" y1="40" x2="29" y2="44" stroke={color} strokeWidth="2.5" strokeLinecap="round" />
    <line x1="16" y1="8" x2="20" y2="14" stroke={color} strokeWidth="1.8" strokeLinecap="round" />
    <line x1="32" y1="8" x2="28" y2="14" stroke={color} strokeWidth="1.8" strokeLinecap="round" />
  </svg>
);

export const SoftwareMVPBlocks: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const fadeIn = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const cardW = Math.min((width - 160) / 2, 440);
  const cardH = Math.min((height - 300) / 2, 240);
  const gridX = (width - cardW * 2 - 32) / 2;
  const gridY = 160;

  const CARDS: Card[] = [
    {
      label: "WEB DASHBOARD",
      caption: "FastAPI + React 19 + Tailwind",
      icon: <BrowserIcon color={SAGE} />,
      accentColor: SAGE,
      appearFrame: 10,
    },
    {
      label: "iOS APP",
      caption: "SwiftUI · iPhone PWA",
      icon: <PhoneIcon color="rgb(120 180 220)" />,
      accentColor: "rgb(120 180 220)",
      appearFrame: 55,
    },
    {
      label: "ANDROID APP",
      caption: "React Native · Rancher PWA",
      icon: <AndroidIcon color={TERRACOTTA} />,
      accentColor: TERRACOTTA,
      appearFrame: 110,
    },
    {
      label: "SIMULATOR",
      caption: "make demo SEED=42",
      icon: <TerminalIcon color="rgb(210 178 138)" />,
      accentColor: "rgb(210 178 138)",
      appearFrame: 165,
    },
  ];

  const positions = [
    { col: 0, row: 0 },
    { col: 1, row: 0 },
    { col: 0, row: 1 },
    { col: 1, row: 1 },
  ];

  // Typewriter
  const typeProgress = interpolate(frame, [TYPEWRITER_START, TYPEWRITER_END], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const visibleChars = Math.floor(typeProgress * SUBLINE.length);
  const visibleText = SUBLINE.slice(0, visibleChars);

  return (
    <AbsoluteFill style={{ backgroundColor: CREAM_BG, opacity: fadeIn }}>
      {/* Title */}
      <div
        style={{
          position: "absolute",
          top: 48,
          left: 0,
          right: 0,
          textAlign: "center",
          fontFamily: "Georgia, 'Times New Roman', serif",
          fontWeight: 700,
          fontSize: 36,
          color: INK,
          letterSpacing: "-0.01em",
        }}
      >
        Full Software MVP — Built
      </div>

      {/* Cards */}
      {CARDS.map((card, i) => {
        const pos = positions[i];
        const sp = spring({
          frame: frame - card.appearFrame,
          fps,
          config: { damping: 110, stiffness: 160, mass: 0.75 },
        });
        const scaleVal = interpolate(sp, [0, 1], [0.82, 1]);
        const opacityVal = interpolate(sp, [0, 0.05, 1], [0, 0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });

        // All-built pulse after frame 220
        const pulsePhase = frame > 220
          ? (frame - 220 - i * 12) % (fps * 3)
          : 999;
        const isPulsing = pulsePhase < 20;
        const pulseGlow = isPulsing
          ? interpolate(pulsePhase, [0, 10, 20], [0, 0.7, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            })
          : 0;

        const left = gridX + pos.col * (cardW + 32);
        const top = gridY + pos.row * (cardH + 28);

        return (
          <div
            key={card.label}
            style={{
              position: "absolute",
              left,
              top,
              width: cardW,
              height: cardH,
              backgroundColor: CREAM_CARD,
              border: `2px solid ${card.accentColor}`,
              borderRadius: 18,
              padding: "24px 28px",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
              transform: `scale(${scaleVal})`,
              opacity: opacityVal,
              transformOrigin: "center center",
              boxShadow: `0 4px 20px rgba(0,0,0,0.1)${pulseGlow > 0 ? `, 0 0 ${Math.round(20 * pulseGlow)}px ${card.accentColor}` : ""}`,
            }}
          >
            {/* Icon + label row */}
            <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
              {card.icon}
              <div
                style={{
                  fontFamily: MONO,
                  fontWeight: 800,
                  fontSize: 16,
                  color: INK,
                  letterSpacing: "0.14em",
                  textTransform: "uppercase",
                }}
              >
                {card.label}
              </div>
            </div>

            {/* Caption */}
            <div
              style={{
                fontFamily: MONO,
                fontSize: 14,
                color: card.accentColor,
                letterSpacing: "0.06em",
                borderTop: `1px solid ${card.accentColor}40`,
                paddingTop: 10,
              }}
            >
              {card.caption}
            </div>
          </div>
        );
      })}

      {/* Typewriter sub-line */}
      <div
        style={{
          position: "absolute",
          bottom: 44,
          left: gridX,
          right: gridX,
          fontFamily: MONO,
          fontSize: 14,
          color: INK_LIGHT,
          letterSpacing: "0.05em",
          lineHeight: 1.5,
          minHeight: 44,
        }}
      >
        {visibleText}
        {typeProgress < 1 && frame > TYPEWRITER_START && (
          <span
            style={{
              display: "inline-block",
              width: 2,
              height: "1em",
              backgroundColor: SAGE,
              marginLeft: 2,
              verticalAlign: "text-bottom",
              opacity: Math.floor(frame / 8) % 2 === 0 ? 1 : 0,
            }}
          />
        )}
      </div>
    </AbsoluteFill>
  );
};
