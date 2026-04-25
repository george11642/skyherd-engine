/**
 * v2 — Variants A & B Act 1 (Setup, 60s).
 *
 * Both variants share the same skeleton: cold-open hook (8s, no VO) → intro
 * VO (~14-16s) → market context (28s, B-roll cuts) → bridge to demo (10s).
 *
 * The only divergence is the hook (kinetic typography) and the intro/bridge
 * VO files. Variant prop selects.
 */
import {
  AbsoluteFill,
  Audio,
  Sequence,
  Video,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {
  AB_LAYOUT,
  type Variant,
  type VoDurationsFrames,
} from "../../compositions/calculate-main-metadata";
import { ACCENT_MAP, KineticPunch, useFadeInOut } from "./shared";

type Props = {
  variant: Variant;
  voDurationsFrames: VoDurationsFrames;
};

const FPS = 30;

// ── Beat 1A — Variant A cold open: contrarian punch (8s, no VO) ──────────────
const HookContrarian = () => (
  <AbsoluteFill
    style={{
      backgroundColor: "rgb(248 244 234)", // CrossBeam-cream
      alignItems: "center",
      justifyContent: "center",
    }}
  >
    <KineticPunch
      words={[
        {
          text: "Everyone thinks",
          appearFrame: 15,
          weight: 500,
          size: 56,
          color: "rgb(60 72 56)",
        },
        {
          text: "ranchers need smarter sensors.",
          appearFrame: 45,
          weight: 500,
          size: 56,
          color: "rgb(60 72 56)",
        },
        {
          text: "They don't.",
          appearFrame: 105,
          weight: 800,
          size: 86,
          color: ACCENT_MAP.sage,
        },
        {
          text: "They need a nervous system.",
          appearFrame: 165,
          weight: 800,
          size: 86,
          color: ACCENT_MAP.dust,
        },
      ]}
    />
  </AbsoluteFill>
);

// ── Beat 1B — Variant B cold open: metric punch (8s, no VO) ──────────────────
const HookMetric = () => (
  <AbsoluteFill
    style={{
      backgroundColor: "rgb(248 244 234)",
      alignItems: "center",
      justifyContent: "center",
    }}
  >
    <KineticPunch
      words={[
        {
          text: "$4.17",
          appearFrame: 15,
          weight: 800,
          size: 220,
          color: ACCENT_MAP.dust,
        },
        {
          text: "a week",
          appearFrame: 45,
          weight: 500,
          size: 48,
          color: "rgb(60 72 56)",
        },
        {
          text: "24 / 7  nervous system",
          appearFrame: 90,
          weight: 800,
          size: 60,
          color: ACCENT_MAP.sage,
        },
        {
          text: "10,000-acre ranch",
          appearFrame: 165,
          weight: 600,
          size: 42,
          color: "rgb(60 72 56)",
        },
      ]}
    />
  </AbsoluteFill>
);

// ── Beat 2 — Identity / project credibility (intro VO, ~14-16s) ──────────────
const IntroBeat = ({ variant }: { variant: Variant }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const opacity = useFadeInOut(durationInFrames, 18, 18);
  const voFile =
    variant === "B"
      ? "voiceover/vo-intro-B.mp3"
      : "voiceover/vo-intro.mp3";

  // Slow zoom on dawn-corral B-roll (placeholder — Phase D fetches actual MP4).
  // Until then we degrade gracefully to ambient_establish.mp4 — the v1 clip.
  const zoom = interpolate(frame, [0, durationInFrames], [1.0, 1.12]);

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(8 10 14)", opacity }}>
      <Audio src={staticFile(voFile)} />
      <div
        style={{
          width: "100%",
          height: "100%",
          transform: `scale(${zoom})`,
        }}
      >
        <Video
          src={staticFile("clips/ambient_establish.mp4")}
          startFrom={0}
          endAt={durationInFrames + 60}
          muted
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            filter: "saturate(0.92) contrast(1.04)",
          }}
        />
      </div>
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(10,12,16,0) 50%, rgba(10,12,16,0.85) 100%)",
        }}
      />

      {/* Lower-third: George Teifel · UNM · drone op */}
      <div
        style={{
          position: "absolute",
          bottom: 110,
          left: 90,
          fontFamily: "Inter, sans-serif",
          color: "rgb(236 239 244)",
          opacity: interpolate(frame, [25, 55], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
          display: "flex",
          flexDirection: "column",
          gap: 10,
        }}
      >
        <div
          style={{
            fontSize: 14,
            color: ACCENT_MAP.sage,
            letterSpacing: "0.34em",
            textTransform: "uppercase",
            fontWeight: 600,
          }}
        >
          George Teifel · UNM · Part 107
        </div>
        <div
          style={{
            fontSize: 38,
            fontWeight: 700,
            letterSpacing: "-0.012em",
            maxWidth: 1200,
            lineHeight: 1.1,
          }}
        >
          {variant === "B"
            ? "Five Managed Agents · one ranch · every fence, every trough, every cow."
            : "What if the ranch checked itself?"}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── Beat 3 — Market context (28s, B-roll cuts + kinetic typography hero) ─────
const MARKET_LINES: Array<{ at: number; text: string; color?: string }> = [
  { at: 0, text: "Beef · record highs", color: ACCENT_MAP.dust },
  { at: 180, text: "Cow herd · 65-yr low", color: ACCENT_MAP.dust },
  { at: 360, text: "Labor · gone", color: ACCENT_MAP.sage },
  { at: 540, text: "Eyes · fewer per acre", color: ACCENT_MAP.sage },
  {
    at: 720,
    text: "The herd has a nervous system.\nThe rancher does not.",
    color: ACCENT_MAP.dust,
  },
];

const MarketBeat = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const opacity = useFadeInOut(durationInFrames, 25, 30);

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(8 10 14)", opacity }}>
      <Audio src={staticFile("voiceover/vo-market.mp3")} />
      <Video
        src={staticFile("clips/ambient_establish.mp4")}
        startFrom={0}
        endAt={durationInFrames + 60}
        muted
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          filter: "saturate(0.85) contrast(1.05) brightness(0.65)",
        }}
      />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(6,8,12,0.55) 0%, rgba(6,8,12,0.85) 100%)",
        }}
      />

      {MARKET_LINES.map((line, i) => {
        const inAt = line.at;
        const outAt = line.at + 165;
        const o = interpolate(frame, [inAt, inAt + 18, outAt - 18, outAt], [0, 1, 1, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        const y = interpolate(frame - inAt, [0, 18], [22, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        const isClosing = i === MARKET_LINES.length - 1;
        return (
          <AbsoluteFill
            key={`mline-${i}`}
            style={{
              alignItems: "center",
              justifyContent: "center",
              padding: "0 8%",
              opacity: o,
              transform: `translateY(${y}px)`,
            }}
          >
            <div
              style={{
                fontFamily: "Inter, sans-serif",
                fontWeight: isClosing ? 800 : 700,
                fontSize: isClosing ? 86 : 68,
                color: line.color ?? "rgb(236 239 244)",
                letterSpacing: "-0.02em",
                textAlign: "center",
                lineHeight: 1.1,
                whiteSpace: "pre-line",
                textShadow: "0 6px 28px rgba(0,0,0,0.6)",
              }}
            >
              {line.text}
            </div>
          </AbsoluteFill>
        );
      })}
    </AbsoluteFill>
  );
};

// ── Beat 4 — Bridge to Demo (10s, plays bridge VO + wordmark fade-in) ────────
const BridgeBeat = ({ variant }: { variant: Variant }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const opacity = useFadeInOut(durationInFrames, 20, 20);
  const voFile =
    variant === "B"
      ? "voiceover/vo-bridge-B.mp3"
      : "voiceover/vo-bridge.mp3";

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(10 12 16)", opacity }}>
      <Audio src={staticFile(voFile)} />
      <Video
        src={staticFile("clips/ambient_establish.mp4")}
        startFrom={150}
        endAt={durationInFrames + 200}
        muted
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          opacity: 0.85,
        }}
      />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(10,12,16,0) 45%, rgba(10,12,16,0.78) 100%)",
        }}
      />

      {/* Wordmark bottom-right */}
      <div
        style={{
          position: "absolute",
          bottom: 90,
          right: 100,
          opacity: interpolate(frame, [30, 80], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-end",
          gap: 8,
        }}
      >
        <div
          style={{
            fontFamily: "Inter, sans-serif",
            fontWeight: 800,
            fontSize: 72,
            color: "rgb(236 239 244)",
            letterSpacing: "-0.03em",
            lineHeight: 1,
          }}
        >
          Sky<span style={{ color: ACCENT_MAP.sage }}>Herd</span>
        </div>
        <div
          style={{
            fontFamily: "Inter, sans-serif",
            fontWeight: 500,
            fontSize: 16,
            color: "rgb(168 180 198)",
            letterSpacing: "0.35em",
            textTransform: "uppercase",
          }}
        >
          Ranch A · 40,000 acres
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── Act 1 root (sequences the four beats) ────────────────────────────────────
export const ABAct1Hook = ({ variant, voDurationsFrames }: Props) => {
  // Beat lengths in frames.
  const HOOK = AB_LAYOUT.act1.hook * FPS; // 240
  const introVoSeconds =
    variant === "B"
      ? voDurationsFrames.introB / FPS
      : voDurationsFrames.intro / FPS;
  const INTRO = Math.ceil(
    Math.max(introVoSeconds + 0.5, AB_LAYOUT.act1.introMin) * FPS,
  );
  const MARKET = AB_LAYOUT.act1.marketSlot * FPS;
  const bridgeVoSeconds =
    variant === "B"
      ? voDurationsFrames.bridgeB / FPS
      : voDurationsFrames.bridge / FPS;
  const BRIDGE = Math.ceil(
    Math.max(bridgeVoSeconds + 0.5, AB_LAYOUT.act1.bridgeMin) * FPS,
  );

  return (
    <AbsoluteFill>
      <Sequence from={0} durationInFrames={HOOK} layout="none">
        {variant === "A" ? <HookContrarian /> : <HookMetric />}
      </Sequence>
      <Sequence from={HOOK} durationInFrames={INTRO} layout="none">
        <IntroBeat variant={variant} />
      </Sequence>
      <Sequence from={HOOK + INTRO} durationInFrames={MARKET} layout="none">
        <MarketBeat />
      </Sequence>
      <Sequence
        from={HOOK + INTRO + MARKET}
        durationInFrames={BRIDGE}
        layout="none"
      >
        <BridgeBeat variant={variant} />
      </Sequence>
    </AbsoluteFill>
  );
};
