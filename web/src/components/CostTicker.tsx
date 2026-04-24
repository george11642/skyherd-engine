/**
 * CostTicker — live cost meter with framer-motion animated counter.
 * Shows rate, cumulative total, per-agent strip, and sparkline of last 60 ticks.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { motion, useSpring, useTransform } from "framer-motion";
import { cn } from "@/lib/cn";
import { getSSE, getReplayIfActive } from "@/lib/sse";
import { Sparkline } from "@/components/shared/Sparkline";

interface AgentCost {
  name: string;
  state: string;
  cost_delta_usd: number;
  cumulative_cost_usd: number;
  tokens_in: number;
  tokens_out: number;
}

interface CostTickPayload {
  ts: number;
  seq: number;
  agents: AgentCost[];
  all_idle: boolean;
  rate_per_hr_usd: number;
  total_cumulative_usd: number;
}

const AGENT_SHORT: Record<string, string> = {
  FenceLineDispatcher: "FENCE",
  HerdHealthWatcher: "HEALTH",
  PredatorPatternLearner: "PREDTR",
  GrazingOptimizer: "GRAZNG",
  CalvingWatch: "CALVNG",
};

const MAX_SPARKLINE = 60;

function AnimatedCost({ value }: { value: number }) {
  const spring = useSpring(value, { stiffness: 60, damping: 20 });
  const display = useTransform(spring, (v) => `$${v.toFixed(6)}`);

  useEffect(() => {
    spring.set(value);
  }, [value, spring]);

  return (
    <motion.span
      className="tabnum"
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: "1.375rem",
        fontWeight: 600,
        letterSpacing: "-0.01em",
        color: "var(--color-accent-sage)",
      }}
    >
      {display}
    </motion.span>
  );
}

/**
 * CostTickerProps — all optional; when provided, override the SSE-derived state.
 *
 * This is the test-injection seam used by CostTicker.test.tsx (Plan 05-04 DASH-03).
 * Production callers use `<CostTicker />` with no props and the SSE subscription
 * drives the ticker. Tests (and future storybook fixtures) can bypass SSE by
 * passing `all_idle` / `total_cumulative_usd` / `rate_per_hr_usd` / `agents` /
 * `sparkline` directly.
 */
interface CostTickerProps {
  all_idle?: boolean;
  total_cumulative_usd?: number;
  rate_per_hr_usd?: number;
  agents?: AgentCost[];
  sparkline?: number[];
}

export function CostTicker(props: CostTickerProps = {}) {
  const [tick, setTick] = useState<CostTickPayload | null>(null);
  const sparkRef = useRef<number[]>([]);
  const [sparkline, setSparkline] = useState<number[]>([]);
  // Resolved once on mount — used to override the "PAUSED (idle)" chip when
  // a replay session is running but momentary `all_idle=true` ticks would
  // otherwise label the meter paused (misleading for the recorder + judges).
  const [replay] = useState(() => getReplayIfActive());
  // Tick state for the replay-running override; we re-poll on each cost.tick
  // so a manual pause from the UI flips the label back to PAUSED.
  const [replayRunning, setReplayRunning] = useState<boolean>(
    () => replay !== null && !replay.isPaused(),
  );

  const handleTick = useCallback((payload: CostTickPayload) => {
    setTick(payload);
    sparkRef.current = [...sparkRef.current, payload.rate_per_hr_usd].slice(-MAX_SPARKLINE);
    setSparkline([...sparkRef.current]);
    if (replay !== null) {
      setReplayRunning(!replay.isPaused());
    }
  }, [replay]);

  useEffect(() => {
    const sse = getSSE();
    sse.on("cost.tick", handleTick);
    return () => sse.off("cost.tick", handleTick);
  }, [handleTick]);

  // Prop overrides win over SSE-derived state; falls back to tick payload.
  // In an active replay session we never want to render "PAUSED (idle)" —
  // the user/recorder sees the map animating and the meter labelled paused
  // is contradictory. Replay overrides only the chip/sparkline labelling
  // (they're tied to allIdle), but tests that pass `all_idle` explicitly
  // bypass this — `props.all_idle` still wins.
  const rawAllIdle = props.all_idle ?? tick?.all_idle ?? true;
  const allIdle =
    props.all_idle === undefined && replayRunning ? false : rawAllIdle;
  const totalCost = props.total_cumulative_usd ?? tick?.total_cumulative_usd ?? 0;
  const rateUsd = props.rate_per_hr_usd ?? tick?.rate_per_hr_usd ?? 0;
  const effectiveAgents = props.agents ?? tick?.agents;
  const effectiveSparkline = props.sparkline ?? sparkline;

  return (
    <section
      className="shrink-0 rounded border"
      style={{
        backgroundColor: "var(--color-bg-1)",
        borderColor: allIdle ? "var(--color-line)" : "rgb(148 176 136 / 0.3)",
      }}
      aria-label="Cost meter"
    >
      <div className="px-3 py-2 flex items-center justify-between border-b" style={{ borderColor: "var(--color-line)" }}>
        <span
          className="font-semibold leading-none"
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "0.8125rem",
            letterSpacing: "-0.01em",
            color: "var(--color-text-0)",
          }}
        >
          Cost Meter
        </span>
        <span
          className={cn("chip", allIdle ? "chip-muted" : "chip-sage")}
        >
          {allIdle ? (
            <><span className="h-1.5 w-1.5 rounded-full bg-[var(--color-text-2)] shrink-0" aria-hidden="true" />PAUSED (idle)</>
          ) : (
            <><span className="h-1.5 w-1.5 rounded-full bg-[rgb(148_176_136)] pulse-dot shrink-0" aria-hidden="true" />${rateUsd.toFixed(2)}/hr</>
          )}
        </span>
      </div>

      <div className="px-3 py-2">
        {/* Main cost + sparkline */}
        <div className="flex items-end justify-between gap-3">
          <div className="flex items-baseline gap-2">
            <motion.span
              animate={{
                opacity: allIdle ? 0.4 : 1,
                filter: allIdle ? "grayscale(1)" : "grayscale(0)",
              }}
              transition={{ duration: 0.4, ease: "easeOut" }}
              style={{
                display: "inline-block",
                // Inline-style fallback: framer-motion drives the eased
                // transition, but the resting-state style must be applied
                // synchronously so SSR / jsdom / screenshot readers see the
                // paused treatment even without a RAF loop.
                opacity: allIdle ? 0.4 : 1,
                filter: allIdle ? "grayscale(1)" : "grayscale(0)",
                transition: "opacity 0.4s ease, filter 0.4s ease",
              }}
            >
              <AnimatedCost value={totalCost} />
            </motion.span>
            <span className="text-mono-xs" style={{ color: "var(--color-text-2)" }}>
              cumulative
            </span>
          </div>
          <Sparkline
            values={
              allIdle && effectiveSparkline.length > 0
                ? // Freeze to two identical endpoints — a literal flat
                  // baseline, visually paused, and <=2 distinct coords for
                  // the DASH-03 sparkline-freeze regression guard.
                  [
                    effectiveSparkline[effectiveSparkline.length - 1] ?? 0,
                    effectiveSparkline[effectiveSparkline.length - 1] ?? 0,
                  ]
                : effectiveSparkline
            }
            stroke={allIdle ? "rgb(110 122 140)" : "rgb(148 176 136)"}
          />
        </div>

        {/* Rate line */}
        <div
          className="mt-1 tabnum text-mono-xs"
          style={{ color: "var(--color-text-2)" }}
        >
          {allIdle ? (
            <>Rate: <span style={{ color: "var(--color-text-1)" }}>$0.00/hr</span> — <span style={{ color: "var(--color-warn)" }}>paused</span></>
          ) : (
            <>Rate: <span style={{ color: "var(--color-accent-sage)" }}>$0.08/hr</span> per active session</>
          )}
        </div>

        {/* Per-agent strip */}
        {effectiveAgents && (
          <div className="grid grid-cols-5 gap-1 mt-2" role="list" aria-label="Agent cost breakdown">
            {effectiveAgents.map((a) => (
              <div
                key={a.name}
                role="listitem"
                className="rounded border text-center py-1"
                style={{
                  backgroundColor: a.state === "active" ? "rgb(148 176 136 / 0.08)" : "var(--color-bg-2)",
                  borderColor: a.state === "active" ? "rgb(148 176 136 / 0.3)" : "var(--color-line)",
                  opacity: allIdle ? 0.45 : 1,
                  transition: "opacity 0.4s ease",
                }}
                title={`${a.name}: ${a.state} — $${a.cumulative_cost_usd.toFixed(6)}`}
              >
                <div
                  className="tabnum truncate px-0.5"
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.5625rem",
                    color: a.state === "active" ? "var(--color-accent-sage)" : "var(--color-text-2)",
                    letterSpacing: "0.03em",
                  }}
                >
                  {AGENT_SHORT[a.name] ?? a.name.slice(0, 5)}
                </div>
                <div
                  className="mt-0.5"
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.625rem",
                    color: a.state === "active" ? "var(--color-accent-sage)" : "var(--color-text-2)",
                  }}
                  aria-label={a.state}
                >
                  {a.state === "active" ? "●" : "○"}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
