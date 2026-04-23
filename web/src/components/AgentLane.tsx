/**
 * AgentLane — one vertical lane for a single SkyHerd Managed Agent.
 * Redesigned: dense, ops-console style, Fraunces agent name, sage active border.
 */

import { useRef, useEffect } from "react";
import { cn } from "@/lib/cn";
import { Sparkline } from "@/components/shared/Sparkline";

export interface AgentEvent {
  ts: number;
  message: string;
  level?: string;
  state?: string;
}

export interface AgentLaneProps {
  agentName: string;
  state: "active" | "idle" | "checkpointed";
  lastWake?: number;
  events: AgentEvent[];
  /** Events-per-second ring buffer (length ~30) — right-aligned sparkline in header. */
  eventRate?: number[];
  className?: string;
}

// Short names for mono display
const AGENT_SHORT: Record<string, string> = {
  FenceLineDispatcher: "FENCE",
  HerdHealthWatcher: "HEALTH",
  PredatorPatternLearner: "PREDATOR",
  GrazingOptimizer: "GRAZING",
  CalvingWatch: "CALVING",
};

function formatTime(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export function AgentLane({
  agentName,
  state,
  lastWake,
  events,
  eventRate,
  className,
}: AgentLaneProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const isActive = state === "active";
  const isCheckpointed = state === "checkpointed";

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [events.length]);

  return (
    <div
      data-test="agent-lane"
      data-agent={agentName}
      className={cn(
        "flex flex-col border-b transition-all duration-240",
        isActive
          ? "bg-[rgb(148_176_136/0.04)] border-l-2 border-l-[rgb(148_176_136/0.6)]"
          : "border-l-2 border-l-transparent",
        "border-b-[var(--color-line)]",
        "last:border-b-0",
        className,
      )}
      style={{ borderBottomColor: "var(--color-line)" }}
    >
      {/* Header row */}
      <div className="flex items-center gap-2 px-3 pt-2 pb-1 shrink-0">
        {/* Status dot */}
        <span
          className={cn(
            "h-1.5 w-1.5 rounded-full shrink-0",
            isActive ? "bg-[rgb(148_176_136)] pulse-dot" : "bg-[rgb(38_45_58)]",
          )}
          aria-hidden="true"
        />

        {/* Agent name — Fraunces */}
        <span
          className="text-xs font-semibold truncate flex-1 leading-none"
          style={{
            fontFamily: "var(--font-display)",
            color: isActive ? "var(--color-text-0)" : "var(--color-text-1)",
            letterSpacing: "-0.01em",
          }}
        >
          {agentName}
        </span>

        {/* State chip */}
        <span
          className={cn(
            "chip shrink-0",
            isActive ? "chip-sage" : isCheckpointed ? "chip-sky" : "chip-muted",
          )}
          style={{ fontSize: "0.625rem" }}
        >
          {state}
        </span>

        {/* Event-rate sparkline (last 30s) — hidden when empty */}
        {eventRate && eventRate.length >= 2 && (
          <Sparkline
            values={eventRate}
            width={48}
            height={16}
            stroke={isActive ? "rgb(148 176 136)" : "rgb(110 122 140)"}
            className="shrink-0 opacity-70"
          />
        )}

        {/* Last wake timestamp */}
        {lastWake !== undefined && (
          <span
            className="tabnum shrink-0 hidden sm:inline"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "0.625rem",
              color: "var(--color-text-2)",
            }}
          >
            {formatTime(lastWake)}
          </span>
        )}
      </div>

      {/* Log lines */}
      <div
        ref={scrollRef}
        className="log-scroll px-3 pb-2"
        style={{ maxHeight: "72px" }}
        aria-label={`Log for ${agentName}`}
        role="log"
        aria-live="polite"
      >
        {events.length === 0 ? (
          <div
            data-testid="agent-lane-skeleton"
            className="flex flex-col"
            style={{ gap: "6px", paddingTop: "2px" }}
            aria-label="waiting for events"
          >
            <div className="skeleton" style={{ height: 10, width: "70%" }} />
            <div className="skeleton" style={{ height: 10, width: "45%" }} />
            <div className="skeleton" style={{ height: 10, width: "60%" }} />
            <span className="sr-only">waiting for events</span>
          </div>
        ) : (
          events.slice(-20).map((ev, idx) => (
            <div
              key={idx}
              className="flex gap-2 leading-relaxed log-enter"
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.6875rem",
                color: ev.level === "ERROR"
                  ? "var(--color-danger)"
                  : "var(--color-text-1)",
              }}
            >
              <span style={{ color: "var(--color-text-2)" }} className="shrink-0 tabnum">
                {formatTime(ev.ts)}
              </span>
              <span style={{ color: ev.level === "ERROR" ? "var(--color-danger)" : "var(--color-text-0)" }}>
                {ev.message}
              </span>
            </div>
          ))
        )}
      </div>

      {/* Short label for the collapsed footer view */}
      <span className="sr-only">{AGENT_SHORT[agentName] ?? agentName}</span>
    </div>
  );
}
