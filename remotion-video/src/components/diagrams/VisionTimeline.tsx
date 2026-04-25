/**
 * VisionTimeline v2 — Scene 8, 22s / 660 frames @ 30fps
 *
 * Animation:
 *  0–90f    : fade-in + L→R line draws
 *  0f       : TODAY reveals   (frame 0)
 *  150f     : 6 MONTHS reveals
 *  330f     : 1 YEAR reveals
 *  510f     : 5 YEARS reveals
 *  570–660f : hold-final (completely still)
 *  ongoing  : TODAY dot pulse, 5-YEAR grid pulse
 */
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

const CREAM      = "rgb(245 240 230)";
const CREAM_DARK = "rgb(210 200 185)";
const SAGE       = "rgb(148 176 136)";
const TERRACOTTA = "rgb(188 90 60)";
const INK        = "rgb(45 42 38)";
const INK_LIGHT  = "rgb(110 105 96)";
const MONO       = "ui-monospace, 'JetBrains Mono', monospace";
const SERIF      = "Georgia, 'Times New Roman', serif";

const LINE_REVEAL_END  = 90;                   // 3s — line draws L→R
const REVEAL_FRAMES    = [0, 150, 330, 510] as const;
const HOLD_FINAL_START = 570;                  // 19s — freeze everything

// ── SVG illustrations (each 120×80 viewBox) ──────────────────────────────────

const LaptopSVG = () => (
  <svg viewBox="0 0 120 80" width={120} height={80}>
    <rect x={8} y={4} width={104} height={62} rx={5} fill={INK} stroke={SAGE} strokeWidth={1.5} />
    <rect x={13} y={9} width={94} height={52} rx={2} fill="rgb(28 32 28)" />
    <text x={18} y={23} fontFamily={MONO} fontSize={6} fill={SAGE}>$ make demo SEED=42</text>
    <text x={18} y={33} fontFamily={MONO} fontSize={6} fill="rgb(130 160 118)">▶ 5 scenarios queued</text>
    <text x={18} y={43} fontFamily={MONO} fontSize={6} fill={SAGE}>✓ coyote … 0.41s</text>
    <text x={18} y={53} fontFamily={MONO} fontSize={6} fill="rgb(130 160 118)">✓ health … 0.38s</text>
    <rect x={18} y={57} width={5} height={6} rx={1} fill={SAGE} opacity={0.85} />
    <rect x={2} y={66} width={116} height={8} rx={4} fill="rgb(80 78 72)" stroke={CREAM_DARK} strokeWidth={1} />
    <rect x={44} y={68} width={32} height={4} rx={2} fill="rgb(100 96 90)" />
  </svg>
);

// NM outline: approximated polygon
const NM_POINTS = "22,8 98,14 100,62 82,62 82,72 22,68";
const NMSVG = () => (
  <svg viewBox="0 0 120 80" width={120} height={80}>
    <polygon points={NM_POINTS} fill="rgb(60 90 55)" stroke={SAGE} strokeWidth={2} strokeLinejoin="round" />
    <circle cx={57} cy={40} r={7} fill={TERRACOTTA} />
    <circle cx={57} cy={40} r={11} fill="none" stroke={TERRACOTTA} strokeWidth={1.5} opacity={0.5} />
    <text x={57} y={62} textAnchor="middle" fontFamily={MONO} fontSize={8} fill={SAGE} letterSpacing="0.12em">PILOT</text>
  </svg>
);

// Simplified US polygon + 10 dots + 2 LoRa antennas
const US_PATH = "M8,24 L20,18 L38,16 L55,14 L70,16 L88,18 L100,24 L108,28 L112,36 L108,44 L100,52 L88,58 L72,62 L55,64 L38,60 L20,54 L10,48 L6,38Z";
const US_DOTS_10 = [{x:22,y:46},{x:30,y:42},{x:18,y:36},{x:28,y:32},{x:40,y:38},{x:48,y:30},{x:60,y:44},{x:70,y:36},{x:82,y:40},{x:56,y:54}];
const ANTENNA_PTS = [{x:25,y:27},{x:72,y:28}];

const US10SVG = () => (
  <svg viewBox="0 0 120 80" width={120} height={80}>
    <path d={US_PATH} fill="rgb(55 80 50)" stroke={SAGE} strokeWidth={1.5} strokeLinejoin="round" />
    {US_DOTS_10.map((d, i) => (
      <g key={i}>
        <circle cx={d.x} cy={d.y} r={3.5} fill={SAGE} />
        <circle cx={d.x} cy={d.y} r={6} fill="none" stroke={SAGE} strokeWidth={1} opacity={0.4} />
      </g>
    ))}
    {ANTENNA_PTS.map((p, i) => (
      <g key={i}>
        <line x1={p.x} y1={p.y+5} x2={p.x} y2={p.y-2} stroke="rgb(100 130 90)" strokeWidth={1.5} strokeLinecap="round" />
        <line x1={p.x-4} y1={p.y+3} x2={p.x} y2={p.y-2} stroke="rgb(100 130 90)" strokeWidth={1} strokeLinecap="round" />
        <line x1={p.x+4} y1={p.y+3} x2={p.x} y2={p.y-2} stroke="rgb(100 130 90)" strokeWidth={1} strokeLinecap="round" />
      </g>
    ))}
  </svg>
);

// US outline with dense grid + pulsing rings
const GRID_DOTS: Array<{cx:number;cy:number}> = [];
for (let r = 0; r < 5; r++) for (let c = 0; c < 8; c++) {
  const cx = 12 + c * 13, cy = 20 + r * 10;
  if (cx > 8 && cx < 112 && cy > 16 && cy < 62) GRID_DOTS.push({cx, cy});
}
const PULSE_DOTS = [{cx:22,cy:40},{cx:55,cy:30},{cx:90,cy:38}];

const US5YearSVG: React.FC<{pulse: number}> = ({ pulse }) => (
  <svg viewBox="0 0 120 80" width={120} height={80}>
    <path d={US_PATH} fill="rgb(45 70 42)" stroke={SAGE} strokeWidth={1.5} strokeLinejoin="round" />
    {GRID_DOTS.map((d, i) => (
      <circle key={i} cx={d.cx} cy={d.cy} r={2.8} fill={SAGE} opacity={0.7 + pulse * 0.3} />
    ))}
    {PULSE_DOTS.map((d, i) => (
      <circle key={i} cx={d.cx} cy={d.cy} r={6 + pulse * 3} fill="none"
        stroke={TERRACOTTA} strokeWidth={1} opacity={0.35 + pulse * 0.3} />
    ))}
  </svg>
);

// ── Milestone data ────────────────────────────────────────────────────────────

interface Milestone { label: string; sub: string; isNow: boolean; xFrac: number }

const MILESTONES: Milestone[] = [
  { label: "TODAY",    sub: "Software MVP · Simulator",      isNow: true,  xFrac: 0.07 },
  { label: "6 MONTHS", sub: "Pilot ranches · NM",            isNow: false, xFrac: 0.36 },
  { label: "1 YEAR",   sub: "10 ranches · Pi cameras · LoRa",isNow: false, xFrac: 0.65 },
  { label: "5 YEARS",  sub: "Every ranch in America",         isNow: false, xFrac: 0.93 },
];

// ── Component ─────────────────────────────────────────────────────────────────

export const VisionTimeline: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const frozen    = frame >= HOLD_FINAL_START;
  const liveFrame = frozen ? HOLD_FINAL_START - 1 : frame;

  const fadeIn = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  const lineProgress = frozen ? 1 : interpolate(frame, [0, LINE_REVEAL_END], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  // TODAY pulse (stops in hold-final)
  const todayPulse = (!frozen && liveFrame > 90)
    ? Math.sin(((liveFrame - 90) / fps) * Math.PI * 1.4) * 0.25 + 0.75
    : 0.75;

  // 5-YEAR grid pulse
  const fiveYearPulse = frozen ? 0.5 : interpolate(
    Math.sin(((liveFrame - REVEAL_FRAMES[3]) / fps) * Math.PI * 0.8),
    [-1, 1], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const timelineY  = height * 0.52;
  const tlLeft     = width  * 0.06;
  const tlRight    = width  * 0.94;
  const tlW        = tlRight - tlLeft;
  const dotR       = 18;
  const CARD_W     = 138;

  return (
    <AbsoluteFill style={{ backgroundColor: CREAM, opacity: fadeIn }}>

      {/* Title */}
      <div style={{
        position: "absolute", top: 48, left: 0, right: 0,
        textAlign: "center", fontFamily: SERIF, fontWeight: 700,
        fontSize: 46, color: INK, letterSpacing: "-0.01em",
      }}>
        The Road Ahead
      </div>

      {/* SVG: track + animated line + dots */}
      <svg style={{ position: "absolute", inset: 0, overflow: "visible" }}
        viewBox={`0 0 ${width} ${height}`} width={width} height={height}>
        <line x1={tlLeft} y1={timelineY} x2={tlRight} y2={timelineY}
          stroke={CREAM_DARK} strokeWidth={7} strokeLinecap="round" />
        <line x1={tlLeft} y1={timelineY} x2={tlLeft + tlW * lineProgress} y2={timelineY}
          stroke={SAGE} strokeWidth={7} strokeLinecap="round" />

        {MILESTONES.map((m, i) => {
          const dotX    = tlLeft + m.xFrac * tlW;
          const revealF = REVEAL_FRAMES[i];
          const visible = frame >= revealF;
          const sp = spring({ frame: liveFrame - revealF, fps,
            config: { damping: 120, stiffness: 200, mass: 0.6 } });
          const dotOp  = visible ? interpolate(sp, [0, 1], [0, 1], {
            extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 0;
          const dotScl = visible ? (m.isNow
            ? 1 + (todayPulse - 0.75) * 0.5
            : interpolate(sp, [0, 1], [0.4, 1], {
                extrapolateLeft: "clamp", extrapolateRight: "clamp" })) : 0;
          const col = m.isNow ? TERRACOTTA : SAGE;
          return (
            <g key={m.label} opacity={dotOp}>
              {m.isNow && <>
                <circle cx={dotX} cy={timelineY} r={dotR * 2.2 * (1 + (todayPulse - 0.75) * 0.3)}
                  fill="none" stroke={TERRACOTTA} strokeWidth={2} opacity={0.3 * todayPulse} />
                <circle cx={dotX} cy={timelineY} r={dotR * 1.6}
                  fill="none" stroke={TERRACOTTA} strokeWidth={1.5} opacity={0.2} />
              </>}
              <circle cx={dotX} cy={timelineY} r={dotR * dotScl} fill={col} />
              <line x1={dotX} y1={timelineY - dotR} x2={dotX} y2={timelineY - dotR - 28}
                stroke={col} strokeWidth={2.5} strokeLinecap="round" opacity={dotOp} />
            </g>
          );
        })}
      </svg>

      {/* Milestone labels + illustrations (DOM) */}
      {MILESTONES.map((m, i) => {
        const dotX    = tlLeft + m.xFrac * tlW;
        const revealF = REVEAL_FRAMES[i];
        const visible = frame >= revealF;
        const sp = spring({ frame: liveFrame - revealF, fps,
          config: { damping: 120, stiffness: 200, mass: 0.6 } });
        const op = visible ? interpolate(sp, [0, 1], [0, 1], {
          extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 0;
        const dy = visible ? interpolate(sp, [0, 1], [-18, 0], {
          extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : -18;

        // TODAY + 1 YEAR above timeline; 6 MONTHS + 5 YEARS below
        const isAbove   = i % 2 === 0;
        const vertBase  = isAbove ? -210 : 60;

        const IllustBox = ({ children }: { children: React.ReactNode }) => (
          <div style={{
            display: "flex", justifyContent: "center",
            background: "rgba(55 75 50 / 0.07)",
            borderRadius: 10, padding: "7px 5px",
            marginTop: isAbove ? 0 : 10,
            marginBottom: isAbove ? 10 : 0,
          }}>
            {children}
          </div>
        );

        return (
          <div key={`ms-${i}`} style={{
            position: "absolute",
            left: dotX - CARD_W / 2,
            top: timelineY + vertBase,
            width: CARD_W,
            textAlign: "center",
            opacity: op,
            transform: `translateY(${dy}px)`,
          }}>
            {isAbove && (
              <IllustBox>
                {i === 0 && <LaptopSVG />}
                {i === 2 && <US10SVG />}
              </IllustBox>
            )}
            <div style={{
              fontFamily: MONO, fontWeight: 800,
              fontSize: m.isNow ? 26 : 22,
              color: m.isNow ? TERRACOTTA : INK,
              letterSpacing: "0.12em", textTransform: "uppercase",
              marginBottom: 6,
            }}>
              {m.label}
            </div>
            <div style={{
              fontFamily: SERIF, fontSize: 18,
              color: INK_LIGHT, lineHeight: 1.4,
              marginBottom: isAbove ? 0 : 8,
            }}>
              {m.sub}
            </div>
            {!isAbove && (
              <IllustBox>
                {i === 1 && <NMSVG />}
                {i === 3 && <US5YearSVG pulse={fiveYearPulse} />}
              </IllustBox>
            )}
          </div>
        );
      })}

      {/* Bottom callout */}
      <div style={{
        position: "absolute", bottom: 42, left: 0, right: 0,
        textAlign: "center", fontFamily: MONO, fontSize: 17,
        color: SAGE, letterSpacing: "0.13em", textTransform: "uppercase",
        opacity: interpolate(
          frame,
          [REVEAL_FRAMES[3] + 60, REVEAL_FRAMES[3] + 120],
          [0, 1],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
        ),
      }}>
        Every ranch in America deserves a nervous system
      </div>

    </AbsoluteFill>
  );
};
