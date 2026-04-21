/**
 * AgentLane — one horizontal log lane for a single SkyHerd Managed Agent.
 */

import { useRef, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/cn";

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
  className?: string;
}

const STATE_COLORS = {
  active: "success" as const,
  idle: "muted" as const,
  checkpointed: "outline" as const,
};

const AGENT_ICONS: Record<string, string> = {
  FenceLineDispatcher: "⚡",
  HerdHealthWatcher: "🐄",
  PredatorPatternLearner: "🦊",
  GrazingOptimizer: "🌿",
  CalvingWatch: "🍃",
};

function formatTime(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export function AgentLane({ agentName, state, lastWake, events, className }: AgentLaneProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new events
  useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [events.length]);

  const icon = AGENT_ICONS[agentName] ?? "◆";
  const isActive = state === "active";

  return (
    <div
      data-test="agent-lane"
      data-agent={agentName}
      className={cn(
        "flex flex-col border-b border-slate-700/40 last:border-b-0",
        isActive ? "bg-slate-800/30" : "bg-transparent",
        className,
      )}
    >
      {/* Header row */}
      <div className="flex items-center gap-2 px-3 py-1.5 shrink-0">
        {/* Active pulse dot */}
        <span className="flex items-center gap-1.5">
          <span
            className={cn(
              "h-1.5 w-1.5 rounded-full",
              isActive ? "bg-green-400 pulse-dot" : "bg-slate-600",
            )}
            aria-hidden="true"
          />
        </span>
        <span className="text-base leading-none" aria-hidden="true">{icon}</span>
        <span className="text-xs font-semibold text-slate-200 truncate flex-1">{agentName}</span>
        <Badge variant={STATE_COLORS[state]}>{state}</Badge>
        {lastWake !== undefined && (
          <span className="text-xs text-slate-500 shrink-0">
            {formatTime(lastWake)}
          </span>
        )}
      </div>

      {/* Log lines */}
      <div
        ref={scrollRef}
        className="log-scroll flex-1 min-h-0 px-3 pb-1.5 overflow-y-auto"
        style={{ maxHeight: "72px" }}
        aria-label={`Log for ${agentName}`}
      >
        {events.length === 0 ? (
          <p className="text-xs text-slate-600 italic">waiting for events…</p>
        ) : (
          events
            .slice(-20)
            .map((ev, idx) => (
              <div
                key={idx}
                className={cn(
                  "flex gap-2 text-xs font-mono leading-relaxed",
                  ev.level === "ERROR" ? "text-red-400" : "text-slate-400",
                )}
              >
                <span className="text-slate-600 shrink-0">{formatTime(ev.ts)}</span>
                <span className="text-slate-300">{ev.message}</span>
              </div>
            ))
        )}
      </div>
    </div>
  );
}
