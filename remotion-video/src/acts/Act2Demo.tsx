import {
  AbsoluteFill,
  Audio,
  Easing,
  Loop,
  Sequence,
  Series,
  Video,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import type { VoDurationsFrames } from "../compositions/calculate-main-metadata";

type Act2Props = {
  voDurationsFrames: VoDurationsFrames;
};

const FPS = 30;

// ── Shared lower-third card (fades in, stays, fades out) ─────────────────────
type LowerThirdProps = {
  agent: string;
  detail: string;
  accent: "sage" | "dust" | "sky" | "thermal" | "warn";
  appearFrame: number;
  durationInFrames: number;
};

const ACCENT_MAP: Record<LowerThirdProps["accent"], string> = {
  sage: "rgb(148 176 136)",
  dust: "rgb(210 178 138)",
  sky: "rgb(120 180 220)",
  thermal: "rgb(255 143 60)",
  warn: "rgb(240 195 80)",
};

const LowerThird = ({
  agent,
  detail,
  accent,
  appearFrame,
  durationInFrames,
}: LowerThirdProps) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const appearProgress = spring({
    frame: frame - appearFrame,
    fps,
    config: { damping: 120, stiffness: 180, mass: 0.7 },
  });
  const x = interpolate(appearProgress, [0, 1], [-60, 0]);
  const opacity = interpolate(appearProgress, [0, 1], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const exitOpacity = interpolate(
    frame,
    [appearFrame + durationInFrames - 20, appearFrame + durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  return (
    <div
      style={{
        position: "absolute",
        bottom: 90,
        left: 90,
        display: "flex",
        alignItems: "stretch",
        gap: 18,
        transform: `translateX(${x}px)`,
        opacity: Math.min(opacity, exitOpacity),
        backgroundColor: "rgba(16,19,25,0.78)",
        borderRadius: 8,
        backdropFilter: "blur(12px)",
        padding: "18px 26px",
        boxShadow: "0 10px 40px rgba(0,0,0,0.45)",
      }}
    >
      <div
        style={{
          width: 4,
          backgroundColor: ACCENT_MAP[accent],
          borderRadius: 2,
        }}
      />
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <div
          style={{
            fontFamily: "Inter, sans-serif",
            fontWeight: 700,
            fontSize: 24,
            color: "rgb(236 239 244)",
            letterSpacing: "-0.005em",
          }}
        >
          {agent}
        </div>
        <div
          style={{
            fontFamily: "Inter, sans-serif",
            fontWeight: 500,
            fontSize: 18,
            color: "rgb(168 180 198)",
            letterSpacing: "0.02em",
          }}
        >
          {detail}
        </div>
      </div>
    </div>
  );
};

// ── Scrub-anchor chip (HashChip / card reveal) ───────────────────────────────
type AnchorChipProps = {
  label: string;
  value: string;
  appearFrame: number;
  accent: LowerThirdProps["accent"];
};

const AnchorChip = ({ label, value, appearFrame, accent }: AnchorChipProps) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({
    frame: frame - appearFrame,
    fps,
    config: { damping: 100, stiffness: 200 },
  });
  const scale = interpolate(p, [0, 1], [0.92, 1]);
  const opacity = interpolate(p, [0, 1], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        top: 90,
        right: 90,
        transform: `scale(${scale})`,
        opacity,
        fontFamily: "Inter, sans-serif",
        backgroundColor: "rgba(16,19,25,0.86)",
        border: `1px solid ${ACCENT_MAP[accent]}`,
        borderRadius: 8,
        padding: "16px 22px",
        backdropFilter: "blur(10px)",
        boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
      }}
    >
      <div
        style={{
          fontSize: 12,
          color: ACCENT_MAP[accent],
          letterSpacing: "0.3em",
          textTransform: "uppercase",
          marginBottom: 6,
          fontWeight: 600,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: "ui-monospace, JetBrains Mono, monospace",
          fontSize: 22,
          color: "rgb(236 239 244)",
          fontWeight: 500,
        }}
      >
        {value}
      </div>
    </div>
  );
};

// ── Beat: Establish (13 s) ───────────────────────────────────────────────────
const BeatEstablish = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  // Vertical pan via CSS transform.
  const translateY = interpolate(frame, [0, durationInFrames], [0, -120]);

  // Fade in from black over first 25 frames so the Act1→Act2 cut
  // cross-dissolves with Act1's final hold frame.
  const fadeIn = interpolate(frame, [0, 25], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const titleProgress = interpolate(frame, [40, 90], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const titleY = interpolate(titleProgress, [0, 1], [30, 0]);

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(8 10 14)", opacity: fadeIn }}>
      <Audio src={staticFile("voiceover/wes-establish.mp3")} />
      <div
        style={{
          width: "100%",
          height: "100%",
          transform: `translateY(${translateY}px) scale(1.08)`,
        }}
      >
        <Video
          src={staticFile("clips/ambient_establish.mp4")}
          startFrom={100}
          endAt={490}
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
            "linear-gradient(180deg, rgba(10,12,16,0) 55%, rgba(10,12,16,0.85) 100%)",
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: 110,
          left: 90,
          transform: `translateY(${titleY}px)`,
          opacity: titleProgress,
          fontFamily: "Inter, sans-serif",
          display: "flex",
          flexDirection: "column",
          gap: 10,
        }}
      >
        <div
          style={{
            fontSize: 14,
            color: "rgb(148 176 136)",
            letterSpacing: "0.38em",
            textTransform: "uppercase",
            fontWeight: 600,
          }}
        >
          Act II · The Mesh
        </div>
        <div
          style={{
            fontSize: 56,
            fontWeight: 700,
            color: "rgb(236 239 244)",
            letterSpacing: "-0.02em",
            lineHeight: 1.05,
          }}
        >
          One ranch. Five agents. 33 skill files.
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── Beat: Scenario (14 s each) ───────────────────────────────────────────────
type ScenarioProps = {
  clipName: string;
  voFile: string | null;
  voStartFrame: number; // when VO begins within the 14 s slot
  agent: string;
  detail: string;
  accent: LowerThirdProps["accent"];
  anchorLabel: string;
  anchorValue: string;
  anchorFrame: number; // local frame when anchor chip appears
  scenarioNumber: number;
};

const BeatScenario = ({
  clipName,
  voFile,
  voStartFrame,
  agent,
  detail,
  accent,
  anchorLabel,
  anchorValue,
  anchorFrame,
  scenarioNumber,
}: ScenarioProps) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const fadeIn = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 20, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const opacity = Math.min(fadeIn, fadeOut);

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(6 8 12)" }}>
      <div style={{ width: "100%", height: "100%", opacity }}>
        <Video
          src={staticFile(`clips/${clipName}`)}
          startFrom={0}
          endAt={420}
          muted
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
      </div>
      {/* Vignette */}
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(6,8,12,0.55) 100%)",
          opacity,
        }}
      />

      {/* Scenario number badge (top-left) */}
      <div
        style={{
          position: "absolute",
          top: 90,
          left: 90,
          display: "flex",
          alignItems: "center",
          gap: 16,
          opacity: fadeIn,
        }}
      >
        <div
          style={{
            width: 56,
            height: 56,
            borderRadius: 28,
            backgroundColor: ACCENT_MAP[accent],
            color: "rgb(10 12 16)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: "Inter, sans-serif",
            fontWeight: 800,
            fontSize: 28,
          }}
        >
          {scenarioNumber}
        </div>
        <div
          style={{
            fontFamily: "Inter, sans-serif",
            fontSize: 16,
            letterSpacing: "0.32em",
            textTransform: "uppercase",
            color: "rgb(236 239 244)",
            fontWeight: 600,
          }}
        >
          Scenario {scenarioNumber} / 5
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
        appearFrame={150}
        durationInFrames={durationInFrames - 150}
      />
      <AnchorChip
        label={anchorLabel}
        value={anchorValue}
        appearFrame={anchorFrame}
        accent={accent}
      />
    </AbsoluteFill>
  );
};

// ── Beat: Synthesis (32 s) ───────────────────────────────────────────────────
const BeatSynthesis = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const cards: Array<{
    at: number;
    title: string;
    body: string;
    accent: keyof typeof ACCENT_MAP;
  }> = [
    {
      at: 150,
      title: "5 Managed Agents",
      body: "Idle-pause billing. $4.17 / week of Claude.",
      accent: "sage",
    },
    {
      at: 450,
      title: "33 Skill Files",
      body: "Domain knowledge per task. CrossBeam pattern.",
      accent: "dust",
    },
    {
      at: 750,
      title: "Ranch + Mavic + Wes",
      body: "Physical loop. Sim-first. Deterministic replay.",
      accent: "sky",
    },
  ];

  // Extended fade-out (45 frames / 1.5 s) for a deeper cross-dissolve into
  // Act 3 BeatAttest (which also extends its fade-in to 35 frames).
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 45, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(8 10 14)" }}>
      <Audio src={staticFile("voiceover/wes-synthesis.mp3")} />
      <div style={{ width: "100%", height: "100%", opacity: fadeOut }}>
        {/* Clip is only 531 frames (17.7 s) but synthesis slot is ~960 frames
            (32 s). Loop the clip so we never freeze on its last frame. */}
        <Loop durationInFrames={520}>
          <Video
            src={staticFile("clips/ambient_30x_synthesis.mp4")}
            startFrom={0}
            endAt={520}
            muted
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              filter: "saturate(0.9)",
            }}
          />
        </Loop>
      </div>
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(6,8,12,0.35) 0%, rgba(6,8,12,0.82) 100%)",
          opacity: fadeOut,
        }}
      />

      {/* Stacked cards on the right */}
      <div
        style={{
          position: "absolute",
          top: "50%",
          right: 120,
          transform: "translateY(-50%)",
          display: "flex",
          flexDirection: "column",
          gap: 24,
          width: 640,
          opacity: fadeOut,
        }}
      >
        {cards.map((card, i) => {
          const p = spring({
            frame: frame - card.at,
            fps,
            config: { damping: 100, stiffness: 200, mass: 0.7 },
          });
          const x = interpolate(p, [0, 1], [80, 0]);
          const o = interpolate(p, [0, 1], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return (
            <div
              key={`card-${i}`}
              style={{
                transform: `translateX(${x}px)`,
                opacity: o,
                backgroundColor: "rgba(16,19,25,0.82)",
                border: `1px solid ${ACCENT_MAP[card.accent]}`,
                borderLeft: `5px solid ${ACCENT_MAP[card.accent]}`,
                borderRadius: 10,
                padding: "22px 28px",
                backdropFilter: "blur(14px)",
                boxShadow: "0 12px 40px rgba(0,0,0,0.5)",
                fontFamily: "Inter, sans-serif",
              }}
            >
              <div
                style={{
                  fontSize: 14,
                  color: ACCENT_MAP[card.accent],
                  letterSpacing: "0.3em",
                  textTransform: "uppercase",
                  fontWeight: 600,
                  marginBottom: 10,
                }}
              >
                Why it matters · {i + 1}
              </div>
              <div
                style={{
                  fontSize: 34,
                  fontWeight: 700,
                  color: "rgb(236 239 244)",
                  letterSpacing: "-0.015em",
                  marginBottom: 6,
                }}
              >
                {card.title}
              </div>
              <div
                style={{
                  fontSize: 20,
                  color: "rgb(168 180 198)",
                  fontWeight: 500,
                }}
              >
                {card.body}
              </div>
            </div>
          );
        })}
      </div>

      {/* Left headline */}
      <div
        style={{
          position: "absolute",
          left: 100,
          top: 110,
          maxWidth: 640,
          fontFamily: "Inter, sans-serif",
          opacity: fadeOut,
        }}
      >
        <div
          style={{
            fontSize: 14,
            color: "rgb(148 176 136)",
            letterSpacing: "0.38em",
            textTransform: "uppercase",
            fontWeight: 600,
            marginBottom: 18,
          }}
        >
          24 Hours · Compressed
        </div>
        <div
          style={{
            fontSize: 68,
            fontWeight: 800,
            color: "rgb(236 239 244)",
            letterSpacing: "-0.025em",
            lineHeight: 1,
          }}
        >
          The ranch that watches itself.
        </div>
        <div
          style={{
            marginTop: 24,
            fontSize: 22,
            color: "rgb(168 180 198)",
            fontWeight: 500,
            lineHeight: 1.35,
          }}
        >
          Five Managed Agents, coordinated through the dashboard, acting on
          sensor data — autonomously, deterministically, 24/7.
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── Act 2 root ───────────────────────────────────────────────────────────────
export const Act2Demo = ({ voDurationsFrames }: Act2Props) => {
  // Slot lengths (frames)
  const ESTABLISH = 13 * FPS; // 390
  const SCENARIO = 14 * FPS; // 420
  const SYNTHESIS_MIN = 28 * FPS;
  const SYNTHESIS = Math.max(
    voDurationsFrames.synthesis + 2 * FPS,
    SYNTHESIS_MIN,
  );

  return (
    <AbsoluteFill>
      <Series>
        <Series.Sequence durationInFrames={ESTABLISH}>
          <BeatEstablish />
        </Series.Sequence>
        <Series.Sequence durationInFrames={SCENARIO}>
          <BeatScenario
            clipName="coyote.mp4"
            voFile="voiceover/wes-coyote.mp3"
            voStartFrame={150}
            agent="FenceLineDispatcher"
            detail="Coyote · 91% confidence · Fence W-12 · Mavic dispatched"
            accent="thermal"
            anchorLabel="Attest row"
            anchorValue="scenario/coyote/attest_row"
            anchorFrame={360}
            scenarioNumber={1}
          />
        </Series.Sequence>
        <Series.Sequence durationInFrames={SCENARIO}>
          <BeatScenario
            clipName="sick_cow.mp4"
            voFile="voiceover/wes-sick-cow.mp3"
            voStartFrame={150}
            agent="HerdHealthWatcher"
            detail="Cow A014 · pinkeye 83% · Vet packet generated"
            accent="warn"
            anchorLabel="Vet packet"
            anchorValue="scenario/sick_cow/packet"
            anchorFrame={360}
            scenarioNumber={2}
          />
        </Series.Sequence>
        <Series.Sequence durationInFrames={SCENARIO}>
          <BeatScenario
            clipName="water.mp4"
            voFile={null}
            voStartFrame={0}
            agent="GrazingOptimizer"
            detail="Tank 7 pressure drop · IR flyover scheduled"
            accent="sky"
            anchorLabel="IR flyover"
            anchorValue="scenario/water/ir_still"
            anchorFrame={330}
            scenarioNumber={3}
          />
        </Series.Sequence>
        <Series.Sequence durationInFrames={SCENARIO}>
          <BeatScenario
            clipName="calving.mp4"
            voFile="voiceover/wes-calving.mp3"
            voStartFrame={150}
            agent="CalvingWatch"
            detail="Cow 117 · pre-labor · Rancher paged (priority)"
            accent="sage"
            anchorLabel="Behavior trace"
            anchorValue="scenario/calving/trace"
            anchorFrame={360}
            scenarioNumber={4}
          />
        </Series.Sequence>
        <Series.Sequence durationInFrames={SCENARIO}>
          <BeatScenario
            clipName="storm.mp4"
            voFile="voiceover/wes-storm.mp3"
            voStartFrame={150}
            agent="Weather-Redirect"
            detail="Hail ETA 45 min · Paddock B → Shelter 2"
            accent="dust"
            anchorLabel="Redirect plan"
            anchorValue="scenario/storm/paddock_redirect"
            anchorFrame={360}
            scenarioNumber={5}
          />
        </Series.Sequence>
        <Series.Sequence durationInFrames={SYNTHESIS}>
          <BeatSynthesis />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};
