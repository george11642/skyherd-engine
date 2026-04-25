/**
 * v2 — Variant C 5-act layout (20/50/55/35/20 = 180s).
 *
 * Hook (20s) → Story (50s) → Demo (55s, ≤8s/scenario + 15s synthesis) →
 * Substance (35s, dedicated Opus + depth beats) → Close (20s, bookend +
 * wordmark).
 *
 * Word-level kinetic captions throughout — placeholder kinetic-typography
 * hero overlays for now; Phase E1 wires faster-whisper word-timestamps via
 * <KineticCaptions> component (not in Phase C scope).
 */
import {
  AbsoluteFill,
  Audio,
  Sequence,
  Series,
  Video,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { C_LAYOUT } from "../../compositions/calculate-main-metadata";
import {
  ACCENT_MAP,
  type Accent,
  AnchorChip,
  KineticPunch,
  LowerThird,
  useFadeInOut,
} from "./shared";

const FPS = 30;

// ── Act 1 (Hook, 20s) — metric punch + hookC VO ───────────────────────────────

const C_HOOK_PUNCH = C_LAYOUT.act1.punchSeconds * FPS; // 240

const CAct1HookPunch = () => (
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
          size: 240,
          color: ACCENT_MAP.dust,
        },
        {
          text: "/ week",
          appearFrame: 45,
          weight: 500,
          size: 52,
          color: "rgb(60 72 56)",
        },
        {
          text: "24 / 7",
          appearFrame: 90,
          weight: 800,
          size: 96,
          color: ACCENT_MAP.sage,
        },
        {
          text: "nervous system",
          appearFrame: 120,
          weight: 800,
          size: 64,
          color: ACCENT_MAP.sage,
        },
        {
          text: "10,000-acre ranch",
          appearFrame: 165,
          weight: 600,
          size: 44,
          color: "rgb(60 72 56)",
        },
      ]}
    />
  </AbsoluteFill>
);

const CAct1HookVo = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const opacity = useFadeInOut(durationInFrames, 18, 18);
  const zoom = interpolate(frame, [0, durationInFrames], [1.0, 1.1]);

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(8 10 14)", opacity }}>
      <Audio src={staticFile("voiceover/vo-hook-C.mp3")} />
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
        }}
      >
        <div
          style={{
            fontSize: 14,
            color: ACCENT_MAP.sage,
            letterSpacing: "0.34em",
            textTransform: "uppercase",
            fontWeight: 600,
            marginBottom: 10,
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
          Every fence. Every trough. Every cow.
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const CAct1Hook = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  void frame;
  const VO = durationInFrames - C_HOOK_PUNCH;

  return (
    <AbsoluteFill>
      <Sequence from={0} durationInFrames={C_HOOK_PUNCH} layout="none">
        <CAct1HookPunch />
      </Sequence>
      <Sequence from={C_HOOK_PUNCH} durationInFrames={VO} layout="none">
        <CAct1HookVo />
      </Sequence>
    </AbsoluteFill>
  );
};

// ── Act 2 (Story, 50s) — full market arc ─────────────────────────────────────

const STORY_LINES: Array<{ at: number; text: string; size?: number; color?: string }> = [
  { at: 30, text: "Beef · record highs", color: ACCENT_MAP.dust },
  { at: 180, text: "Cow herd · 65-yr low", color: ACCENT_MAP.dust },
  { at: 330, text: "Labor · gone", color: ACCENT_MAP.sage },
  { at: 480, text: "Ranchers · aging out", color: ACCENT_MAP.sage },
  { at: 660, text: "72 hours blind", size: 92, color: ACCENT_MAP.warn },
  {
    at: 900,
    text: "The rancher does not.",
    size: 96,
    color: ACCENT_MAP.dust,
  },
  { at: 1110, text: "So we built one.", size: 64, color: ACCENT_MAP.sage },
];

export const CAct2Story = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const opacity = useFadeInOut(durationInFrames, 30, 30);

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(8 10 14)", opacity }}>
      <Audio src={staticFile("voiceover/vo-story-C.mp3")} />
      <Video
        src={staticFile("clips/ambient_establish.mp4")}
        startFrom={0}
        endAt={durationInFrames + 60}
        muted
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          filter: "saturate(0.85) contrast(1.05) brightness(0.6)",
        }}
      />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(6,8,12,0.55) 0%, rgba(6,8,12,0.82) 100%)",
        }}
      />
      {STORY_LINES.map((line, i) => {
        const inAt = line.at;
        const outAt = line.at + 165;
        const o = interpolate(
          frame,
          [inAt, inAt + 18, outAt - 18, outAt],
          [0, 1, 1, 0],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
        );
        const y = interpolate(frame - inAt, [0, 18], [22, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        return (
          <AbsoluteFill
            key={`s-${i}`}
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
                fontWeight: 800,
                fontSize: line.size ?? 68,
                color: line.color ?? "rgb(236 239 244)",
                letterSpacing: "-0.022em",
                textAlign: "center",
                lineHeight: 1.1,
                textShadow: "0 6px 28px rgba(0,0,0,0.65)",
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

// ── Act 3 (Demo, 55s) — 5 scenarios @ 8s + 15s synthesis ─────────────────────

type CScenarioProps = {
  scenarioNumber: number;
  clipName: string;
  voFile: string | null;
  voStartFrame: number;
  agent: string;
  detail: string;
  accent: Accent;
  anchorLabel: string;
  anchorTopic: string;
  anchorHash: string;
  anchorStatus: string;
};

const CScenario = ({
  scenarioNumber,
  clipName,
  voFile,
  voStartFrame,
  agent,
  detail,
  accent,
  anchorLabel,
  anchorTopic,
  anchorHash,
  anchorStatus,
}: CScenarioProps) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const fadeIn = interpolate(frame, [0, 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 12, durationInFrames],
    [1, 0.25],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const opacity = Math.min(fadeIn, fadeOut);

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(6 8 12)" }}>
      <div style={{ width: "100%", height: "100%", opacity }}>
        <Video
          src={staticFile(`clips/${clipName}`)}
          startFrom={0}
          endAt={300}
          muted
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
      </div>
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(6,8,12,0.55) 100%)",
          opacity,
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 80,
          left: 80,
          display: "flex",
          alignItems: "center",
          gap: 14,
          opacity: fadeIn,
        }}
      >
        <div
          style={{
            width: 48,
            height: 48,
            borderRadius: 24,
            backgroundColor: ACCENT_MAP[accent],
            color: "rgb(10 12 16)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: "Inter, sans-serif",
            fontWeight: 800,
            fontSize: 24,
          }}
        >
          {scenarioNumber}
        </div>
        <div
          style={{
            fontFamily: "Inter, sans-serif",
            fontSize: 14,
            letterSpacing: "0.32em",
            textTransform: "uppercase",
            color: "rgb(236 239 244)",
            fontWeight: 600,
          }}
        >
          {scenarioNumber} / 5
        </div>
      </div>
      {voFile ? (
        <Sequence from={voStartFrame}>
          <Audio src={staticFile(voFile)} />
        </Sequence>
      ) : null}
      <LowerThird
        agent={agent}
        detail={detail}
        accent={accent}
        appearFrame={30}
        durationInFrames={durationInFrames - 30}
      />
      <AnchorChip
        label={anchorLabel}
        topic={anchorTopic}
        hash={anchorHash}
        statusPill={anchorStatus}
        appearFrame={Math.max(120, voStartFrame + 30)}
        accent={accent}
      />
    </AbsoluteFill>
  );
};

const CSynthesisBeat = () => {
  const frame = useCurrentFrame();
  const { durationInFrames, fps } = useVideoConfig();
  const opacity = useFadeInOut(durationInFrames, 15, 15);

  // iter2: short 5s synthesis with three fast cards. No VO — music carries,
  // script retired vo-synthesis-C in the humanize pass.
  const cards = [
    {
      at: 10,
      title: "5 Managed Agents",
      body: "Idle-pause billing.",
      accent: "sage" as Accent,
    },
    {
      at: 40,
      title: "33 Skill Files",
      body: "Per-task knowledge.",
      accent: "dust" as Accent,
    },
    {
      at: 80,
      title: "$4.17 / week",
      body: "24/7 coverage.",
      accent: "sky" as Accent,
    },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(8 10 14)", opacity }}>
      <Video
        src={staticFile("clips/ambient_30x_synthesis.mp4")}
        startFrom={0}
        endAt={durationInFrames + 60}
        muted
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          filter: "saturate(0.9) brightness(0.7)",
        }}
      />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(6,8,12,0.4) 0%, rgba(6,8,12,0.82) 100%)",
        }}
      />
      <div
        style={{
          position: "absolute",
          top: "50%",
          right: 100,
          transform: "translateY(-50%)",
          display: "flex",
          flexDirection: "column",
          gap: 18,
          width: 540,
        }}
      >
        {cards.map((c, i) => {
          const p = spring({
            frame: frame - c.at,
            fps,
            config: { damping: 100, stiffness: 200, mass: 0.7 },
          });
          const x = interpolate(p, [0, 1], [60, 0]);
          const o = interpolate(p, [0, 1], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return (
            <div
              key={`c-${i}`}
              style={{
                transform: `translateX(${x}px)`,
                opacity: o,
                backgroundColor: "rgba(16,19,25,0.86)",
                border: `1px solid ${ACCENT_MAP[c.accent]}`,
                borderLeft: `5px solid ${ACCENT_MAP[c.accent]}`,
                borderRadius: 8,
                padding: "16px 22px",
                fontFamily: "Inter, sans-serif",
              }}
            >
              <div
                style={{
                  fontSize: 28,
                  fontWeight: 700,
                  color: "rgb(236 239 244)",
                  letterSpacing: "-0.012em",
                }}
              >
                {c.title}
              </div>
              <div
                style={{
                  fontSize: 16,
                  color: "rgb(168 180 198)",
                  marginTop: 4,
                  fontWeight: 500,
                }}
              >
                {c.body}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// Deep coyote scenario for variant C — same visual grammar as AB deep beat
// but uses the shared vo-coyote-deep.mp3 and keeps the dense-caption flow.
const CDeepCoyote = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const fadeIn = interpolate(frame, [0, 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 15, durationInFrames],
    [1, 0.25],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const opacity = Math.min(fadeIn, fadeOut);

  const SMS_AT = 19 * 30;
  const smsO = interpolate(frame, [SMS_AT, SMS_AT + 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(6 8 12)" }}>
      <Audio src={staticFile("voiceover/vo-coyote-deep.mp3")} />
      <div style={{ width: "100%", height: "100%", opacity }}>
        <Video
          src={staticFile("clips/coyote.mp4")}
          startFrom={0}
          endAt={durationInFrames + 60}
          muted
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
      </div>
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(6,8,12,0.55) 100%)",
          opacity,
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 80,
          left: 80,
          display: "flex",
          alignItems: "center",
          gap: 14,
          opacity: fadeIn,
        }}
      >
        <div
          style={{
            width: 48,
            height: 48,
            borderRadius: 24,
            backgroundColor: ACCENT_MAP.thermal,
            color: "rgb(10 12 16)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: "Inter, sans-serif",
            fontWeight: 800,
            fontSize: 18,
          }}
        >
          3:14
        </div>
        <div
          style={{
            fontFamily: "Inter, sans-serif",
            fontSize: 14,
            letterSpacing: "0.32em",
            textTransform: "uppercase",
            color: "rgb(236 239 244)",
            fontWeight: 600,
          }}
        >
          Deep scenario · Coyote
        </div>
      </div>
      <LowerThird
        agent="FenceLineDispatcher"
        detail="Coyote · 91% · Mavic dispatched"
        accent="thermal"
        appearFrame={45}
        durationInFrames={durationInFrames - 45}
      />
      <AnchorChip
        label="Attest"
        topic="Fence W-12 breach"
        hash="a7c3…f91e"
        statusPill="Signed"
        appearFrame={22 * 30}
        accent="thermal"
      />
      <div
        style={{
          position: "absolute",
          bottom: 220,
          right: 80,
          opacity: smsO,
          maxWidth: 400,
          backgroundColor: "rgba(30,34,40,0.92)",
          borderRadius: 18,
          border: "1px solid rgba(148,176,136,0.3)",
          padding: "14px 18px",
          fontFamily: "Inter, sans-serif",
          color: "rgb(236 239 244)",
          boxShadow: "0 8px 32px rgba(0,0,0,0.55)",
        }}
      >
        <div
          style={{
            fontSize: 11,
            color: "rgb(148 176 136)",
            letterSpacing: "0.28em",
            textTransform: "uppercase",
            fontWeight: 700,
            marginBottom: 6,
          }}
        >
          SMS · 3:14am
        </div>
        <div style={{ fontSize: 15, lineHeight: 1.35, fontWeight: 500 }}>
          Coyote on W-12. Drone scared it off. Fence intact. You&rsquo;re good.
        </div>
      </div>
    </AbsoluteFill>
  );
};

// Silent montage scene for C — 6-7s kinetic callout, no full VO.
type CMontageProps = {
  clipName: string;
  callout: string;
  agent: string;
  detail: string;
  accent: Accent;
  anchorLabel: string;
  anchorTopic: string;
  anchorHash: string;
  anchorStatus: string;
};

const CMontageScene = ({
  clipName,
  callout,
  agent,
  detail,
  accent,
  anchorLabel,
  anchorTopic,
  anchorHash,
  anchorStatus,
}: CMontageProps) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const fadeIn = interpolate(frame, [0, 6], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 8, durationInFrames],
    [1, 0.2],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const opacity = Math.min(fadeIn, fadeOut);

  const calloutO = interpolate(frame, [12, 28], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(6 8 12)" }}>
      <div style={{ width: "100%", height: "100%", opacity }}>
        <Video
          src={staticFile(`clips/${clipName}`)}
          startFrom={0}
          endAt={200}
          muted
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
      </div>
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at center, rgba(0,0,0,0) 50%, rgba(6,8,12,0.65) 100%)",
          opacity,
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 180,
          left: 0,
          right: 0,
          textAlign: "center",
          padding: "0 8%",
          opacity: calloutO,
        }}
      >
        <div
          style={{
            fontFamily: "Inter, sans-serif",
            fontWeight: 800,
            fontSize: 50,
            color: ACCENT_MAP[accent],
            letterSpacing: "-0.022em",
            lineHeight: 1.1,
            textShadow: "0 6px 30px rgba(0,0,0,0.75)",
          }}
        >
          {callout}
        </div>
      </div>
      <LowerThird
        agent={agent}
        detail={detail}
        accent={accent}
        appearFrame={20}
        durationInFrames={durationInFrames - 20}
      />
      <AnchorChip
        label={anchorLabel}
        topic={anchorTopic}
        hash={anchorHash}
        statusPill={anchorStatus}
        appearFrame={40}
        accent={accent}
      />
    </AbsoluteFill>
  );
};

export const CAct3Demo = () => {
  const DEEP = C_LAYOUT.act3.coyoteDeepMin * FPS; // ~750
  const MONTAGE_TOTAL = C_LAYOUT.act3.montageSeconds * FPS; // 750
  const SCENE = Math.floor(
    MONTAGE_TOTAL / C_LAYOUT.act3.montageSceneCount,
  );
  const SYNTH = C_LAYOUT.act3.synthesisSeconds * FPS; // 150

  // Keep CScenario import alive — it's used nowhere else now but we retain the
  // export for backwards-compat with the caption track generator.
  void CScenario;

  return (
    <AbsoluteFill>
      <Series>
        <Series.Sequence durationInFrames={DEEP}>
          <CDeepCoyote />
        </Series.Sequence>
        <Series.Sequence durationInFrames={SCENE}>
          <CMontageScene
            clipName="sick_cow.mp4"
            callout="A014 — vet packet in 12 seconds"
            agent="HerdHealthWatcher"
            detail="Cow A014 · pinkeye 83%"
            accent="warn"
            anchorLabel="Vet"
            anchorTopic="Cow A014"
            anchorHash="4d82…b03c"
            anchorStatus="Sent"
          />
        </Series.Sequence>
        <Series.Sequence durationInFrames={SCENE}>
          <CMontageScene
            clipName="water.mp4"
            callout="Tank 7 · 8 PSI · drone flew it"
            agent="GrazingOptimizer"
            detail="Tank 7 · pressure drop"
            accent="sky"
            anchorLabel="IR"
            anchorTopic="Tank 7"
            anchorHash="92e1…5a0d"
            anchorStatus="Queued"
          />
        </Series.Sequence>
        <Series.Sequence durationInFrames={SCENE}>
          <CMontageScene
            clipName="calving.mp4"
            callout="117's calving · 3:14am"
            agent="CalvingWatch"
            detail="Cow 117 · pre-labor"
            accent="sage"
            anchorLabel="Trace"
            anchorTopic="Cow 117"
            anchorHash="61bf…2c94"
            anchorStatus="Paged"
          />
        </Series.Sequence>
        <Series.Sequence durationInFrames={SCENE}>
          <CMontageScene
            clipName="storm.mp4"
            callout="Hail 45min · herd → Shelter 2"
            agent="Weather-Redirect"
            detail="Paddock B → Shelter 2"
            accent="dust"
            anchorLabel="Plan"
            anchorTopic="Shelter 2"
            anchorHash="d3a9…7e11"
            anchorStatus="Active"
          />
        </Series.Sequence>
        <Series.Sequence durationInFrames={SYNTH}>
          <CSynthesisBeat />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};

// ── Act 4 (Substance, 35s) — Opus 4.7 (20s) + Depth (15s) ────────────────────

const COpusBeat = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const opacity = useFadeInOut(durationInFrames, 25, 25);

  const lines = [
    "[FenceLineDispatcher]    beta-session-id=fls_8a2f  cache-hit=92%",
    "[HerdHealthWatcher]      beta-session-id=hhw_3c91  cache-hit=88%",
    "[PredatorPatternLearner] beta-session-id=ppl_4d7e  cache-hit=95%",
    "[GrazingOptimizer]       beta-session-id=gop_b211  cache-hit=89%",
    "[CalvingWatch]           beta-session-id=cwc_e604  cache-hit=91%",
    "all 5 idle · cost ticker $4.17/week",
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(8 10 14)", opacity }}>
      <Audio src={staticFile("voiceover/vo-opus-C.mp3")} />

      {/* Left half: title + headline */}
      <div
        style={{
          position: "absolute",
          left: 80,
          top: 80,
          width: "45%",
          fontFamily: "Inter, sans-serif",
        }}
      >
        <div
          style={{
            fontSize: 14,
            color: ACCENT_MAP.sage,
            letterSpacing: "0.34em",
            textTransform: "uppercase",
            fontWeight: 600,
            marginBottom: 16,
          }}
        >
          Act IV · Opus 4.7
        </div>
        <div
          style={{
            fontSize: 50,
            fontWeight: 800,
            color: "rgb(236 239 244)",
            letterSpacing: "-0.022em",
            lineHeight: 1.05,
          }}
        >
          Five Managed Agents.
          <br />
          One platform session each.
          <br />
          <span style={{ color: ACCENT_MAP.sage }}>Idle-pause billing.</span>
        </div>
        <div
          style={{
            marginTop: 30,
            fontSize: 20,
            color: "rgb(168 180 198)",
            fontWeight: 500,
            lineHeight: 1.4,
          }}
        >
          Beta header <code style={{ color: ACCENT_MAP.dust }}>managed-agents-2026-04-01</code>.
          Cache control{" "}
          <code style={{ color: ACCENT_MAP.dust }}>cache_control: ephemeral</code> on
          system + skills prefix.
        </div>
        <div
          style={{
            marginTop: 24,
            fontSize: 18,
            color: ACCENT_MAP.sage,
            fontWeight: 600,
            letterSpacing: "0.02em",
            lineHeight: 1.35,
          }}
        >
          Opus 4.7 also authors the per-word caption styling JSON committed in
          this repo. The text you're reading is editorial output of the model.
        </div>
      </div>

      {/* Right half: terminal stream */}
      <div
        style={{
          position: "absolute",
          right: 80,
          top: 90,
          width: "42%",
          backgroundColor: "rgb(6 8 12)",
          border: `1px solid ${ACCENT_MAP.sage}`,
          borderRadius: 10,
          padding: "22px 26px",
          fontFamily: "ui-monospace, JetBrains Mono, monospace",
          fontSize: 16,
          color: "rgb(180 200 188)",
          lineHeight: 1.7,
          boxShadow: "0 12px 40px rgba(0,0,0,0.55)",
        }}
      >
        <div
          style={{
            color: ACCENT_MAP.sage,
            marginBottom: 14,
            fontSize: 13,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            fontWeight: 700,
          }}
        >
          $ skyherd-mesh smoke
        </div>
        {lines.map((l, i) => {
          const o = interpolate(frame, [60 + i * 30, 75 + i * 30], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return (
            <div key={`l-${i}`} style={{ opacity: o }}>
              {l}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const CDepthBeat = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const opacity = useFadeInOut(durationInFrames, 25, 25);

  const numbers = [
    { at: 30, label: "tests", value: "1,106" },
    { at: 90, label: "coverage", value: "87%" },
    { at: 150, label: "signed events", value: "360" },
    { at: 210, label: "seed", value: "42" },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(8 10 14)", opacity }}>
      <Audio src={staticFile("voiceover/vo-depth-C.mp3")} />
      <Video
        src={staticFile("clips/attest_verify.mp4")}
        startFrom={0}
        endAt={durationInFrames + 60}
        muted
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          filter: "brightness(0.55)",
        }}
      />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(6,8,12,0.55) 0%, rgba(6,8,12,0.85) 100%)",
        }}
      />

      <div
        style={{
          position: "absolute",
          left: 100,
          top: "30%",
          fontFamily: "Inter, sans-serif",
        }}
      >
        <div
          style={{
            fontSize: 14,
            color: ACCENT_MAP.sage,
            letterSpacing: "0.34em",
            textTransform: "uppercase",
            fontWeight: 600,
            marginBottom: 24,
          }}
        >
          Same seed. Same bytes. Every time.
        </div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, auto)",
            columnGap: 80,
            rowGap: 24,
          }}
        >
          {numbers.map((n, i) => {
            const o = interpolate(frame, [n.at, n.at + 18], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            return (
              <div key={`n-${i}`} style={{ opacity: o }}>
                <div
                  style={{
                    fontSize: 76,
                    fontWeight: 800,
                    color: ACCENT_MAP.dust,
                    letterSpacing: "-0.03em",
                    lineHeight: 1,
                  }}
                >
                  {n.value}
                </div>
                <div
                  style={{
                    fontSize: 16,
                    color: "rgb(168 180 198)",
                    letterSpacing: "0.22em",
                    textTransform: "uppercase",
                    fontWeight: 600,
                    marginTop: 6,
                  }}
                >
                  {n.label}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const CAct4Substance = () => {
  const OPUS = C_LAYOUT.act4.opusMin * FPS;
  const DEPTH = C_LAYOUT.act4.depthMin * FPS;

  return (
    <AbsoluteFill>
      <Series>
        <Series.Sequence durationInFrames={OPUS}>
          <COpusBeat />
        </Series.Sequence>
        <Series.Sequence durationInFrames={DEPTH}>
          <CDepthBeat />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};

// ── Act 5 (Close, 20s) — bookend (13s) + wordmark (7s) ───────────────────────

const CCloseBookend = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const opacity = useFadeInOut(durationInFrames, 25, 30);

  const lines = [
    { at: 30, text: "Beef at record highs.", color: ACCENT_MAP.dust },
    { at: 120, text: "Cow herd at a 65-yr low.", color: ACCENT_MAP.dust },
    {
      at: 240,
      text: "Now the ranch can watch itself.",
      color: ACCENT_MAP.sage,
      bold: true,
    },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(8 10 14)", opacity }}>
      <Audio src={staticFile("voiceover/vo-close-C.mp3")} />
      <Video
        src={staticFile("clips/ambient_30x_synthesis.mp4")}
        startFrom={0}
        endAt={durationInFrames + 60}
        muted
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          filter: "saturate(0.85) brightness(0.55)",
        }}
      />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(6,8,12,0.4) 0%, rgba(6,8,12,0.82) 100%)",
        }}
      />
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          padding: "0 8%",
          flexDirection: "column",
          gap: 24,
        }}
      >
        {lines.map((l, i) => {
          const o = interpolate(frame, [l.at, l.at + 22], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          const y = interpolate(frame - l.at, [0, 22], [30, 0], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return (
            <div
              key={`cl-${i}`}
              style={{
                fontFamily: "Inter, sans-serif",
                fontWeight: l.bold ? 800 : 700,
                fontSize: l.bold ? 80 : 56,
                color: l.color,
                letterSpacing: "-0.022em",
                textAlign: "center",
                lineHeight: 1.1,
                opacity: o,
                transform: `translateY(${y}px)`,
                textShadow: "0 6px 28px rgba(0,0,0,0.65)",
              }}
            >
              {l.text}
            </div>
          );
        })}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const CCloseWordmark = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const fadeIn = interpolate(frame, [0, 25], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 25, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const opacity = Math.min(fadeIn, fadeOut);

  const wordmarkP = spring({
    frame: frame - 8,
    fps,
    config: { damping: 120, stiffness: 150, mass: 0.8 },
  });
  const scale = interpolate(wordmarkP, [0, 1], [0.9, 1]);
  const wo = interpolate(wordmarkP, [0, 1], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const linesO = interpolate(frame, [50, 90], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "rgb(248 244 234)",
        alignItems: "center",
        justifyContent: "center",
        opacity,
      }}
    >
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse 70% 55% at 50% 50%, rgba(210,178,138,0.45) 0%, rgba(248,244,234,0) 80%)",
        }}
      />
      <div
        style={{
          transform: `scale(${scale})`,
          opacity: wo,
          fontFamily: "Inter, sans-serif",
          fontWeight: 800,
          fontSize: 200,
          color: "rgb(40 56 44)",
          letterSpacing: "-0.04em",
          lineHeight: 1,
        }}
      >
        Sky<span style={{ color: ACCENT_MAP.sage }}>Herd</span>
      </div>
      <div
        style={{
          marginTop: 50,
          opacity: linesO,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 14,
          fontFamily: "Inter, sans-serif",
          color: "rgb(72 84 76)",
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontSize: 28,
            color: "rgb(132 92 56)",
            fontWeight: 600,
            letterSpacing: "0.02em",
          }}
        >
          github.com/george11642/skyherd-engine
        </div>
        <div
          style={{
            fontSize: 18,
            fontFamily:
              "ui-monospace, JetBrains Mono, Cascadia Code, monospace",
            letterSpacing: "0.02em",
          }}
        >
          MIT · Python 3.11 · TypeScript 5.8 · Opus 4.7 · 1106 tests · 87%
          coverage · Ed25519
        </div>
        <div
          style={{
            fontSize: 16,
            color: "rgb(120 132 124)",
            letterSpacing: "0.24em",
            textTransform: "uppercase",
            fontWeight: 600,
            marginTop: 10,
          }}
        >
          George Teifel · UNM · 2026
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const CAct5Close = () => {
  const BOOK = C_LAYOUT.act5.bookendSeconds * FPS; // 390
  const WORD = C_LAYOUT.act5.wordmarkSeconds * FPS; // 210

  return (
    <AbsoluteFill>
      <Series>
        <Series.Sequence durationInFrames={BOOK}>
          <CCloseBookend />
        </Series.Sequence>
        <Series.Sequence durationInFrames={WORD}>
          <CCloseWordmark />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};
