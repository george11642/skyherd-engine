/**
 * AgentLanes — stacks all 5 SkyHerd agent log lanes, wired to SSE.
 * Redesigned: dense ops-console style with Fraunces headings.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { AgentLane, type AgentEvent } from "@/components/AgentLane";
import { getSSE } from "@/lib/sse";

const RATE_BUCKETS = 30;

const AGENT_NAMES = [
  "FenceLineDispatcher",
  "HerdHealthWatcher",
  "PredatorPatternLearner",
  "GrazingOptimizer",
  "CalvingWatch",
] as const;

type AgentName = (typeof AGENT_NAMES)[number];

interface AgentState {
  state: "active" | "idle" | "checkpointed";
  lastWake?: number;
  events: AgentEvent[];
}

const MAX_EVENTS_PER_AGENT = 50;

function makeInitialState(): Record<AgentName, AgentState> {
  return Object.fromEntries(
    AGENT_NAMES.map((name) => [name, { state: "idle" as const, events: [] }]),
  ) as unknown as Record<AgentName, AgentState>;
}

function makeEmptyRates(): Record<AgentName, number[]> {
  return Object.fromEntries(
    AGENT_NAMES.map((n) => [n, Array<number>(RATE_BUCKETS).fill(0)]),
  ) as unknown as Record<AgentName, number[]>;
}

export function AgentLanes() {
  const [agents, setAgents] = useState<Record<AgentName, AgentState>>(makeInitialState);
  const [eventRates, setEventRates] = useState<Record<AgentName, number[]>>(() => makeEmptyRates());

  // Live counters for the current 1-second bucket — mutated synchronously on
  // each agent.event; flushed into the ring buffer on the 1s interval.
  const currentBucketRef = useRef<Record<AgentName, number>>(
    Object.fromEntries(AGENT_NAMES.map((n) => [n, 0])) as unknown as Record<AgentName, number>,
  );

  // 1-second tick: shift each ring buffer left, push the live count, reset.
  useEffect(() => {
    const id = setInterval(() => {
      setEventRates((prev) => {
        const next = {} as Record<AgentName, number[]>;
        for (const name of AGENT_NAMES) {
          const buf = prev[name];
          const count = currentBucketRef.current[name] ?? 0;
          next[name] = [...buf.slice(1), count];
          currentBucketRef.current[name] = 0;
        }
        return next;
      });
    }, 1000);
    return () => clearInterval(id);
  }, []);

  const handleLog = useCallback((payload: {
    agent: string;
    message: string;
    ts: number;
    state?: string;
    level?: string;
  }) => {
    const name = payload.agent as AgentName;
    if (!AGENT_NAMES.includes(name)) return;

    // Increment the live bucket — flushed into the ring each second.
    currentBucketRef.current[name] = (currentBucketRef.current[name] ?? 0) + 1;

    setAgents((prev) => {
      const existing = prev[name];
      const newEvent: AgentEvent = {
        ts: payload.ts,
        message: payload.message,
        level: payload.level ?? "INFO",
        state: payload.state,
      };
      const newEvents = [...existing.events, newEvent].slice(-MAX_EVENTS_PER_AGENT);
      return {
        ...prev,
        [name]: {
          ...existing,
          state: (payload.state as AgentState["state"]) ?? existing.state,
          lastWake: payload.state === "active" ? payload.ts : existing.lastWake,
          events: newEvents,
        },
      };
    });
  }, []);

  const handleCostTick = useCallback((payload: {
    agents: Array<{ name: string; state: string }>;
    ts: number;
  }) => {
    if (!Array.isArray(payload.agents)) return;
    setAgents((prev) => {
      const next = { ...prev };
      for (const a of payload.agents) {
        const name = a.name as AgentName;
        if (AGENT_NAMES.includes(name)) {
          next[name] = { ...next[name], state: a.state as AgentState["state"] };
        }
      }
      return next;
    });
  }, []);

  useEffect(() => {
    const sse = getSSE();
    sse.on("agent.log", handleLog);
    sse.on("cost.tick", handleCostTick);
    return () => {
      sse.off("agent.log", handleLog);
      sse.off("cost.tick", handleCostTick);
    };
  }, [handleLog, handleCostTick]);

  const activeCount = AGENT_NAMES.filter((n) => agents[n].state === "active").length;

  return (
    <section
      className="flex flex-col overflow-hidden h-full rounded border"
      style={{
        backgroundColor: "var(--color-bg-1)",
        borderColor: "var(--color-line)",
      }}
      aria-label="Agent mesh"
    >
      {/* Section header */}
      <div
        className="flex items-center justify-between px-3 py-2 shrink-0 border-b"
        style={{ borderColor: "var(--color-line)" }}
      >
        <span
          className="font-semibold leading-none"
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "0.875rem",
            letterSpacing: "-0.01em",
            color: "var(--color-text-0)",
          }}
        >
          Agent Mesh
        </span>
        <span
          className="chip chip-muted"
        >
          {activeCount}/{AGENT_NAMES.length} active
        </span>
      </div>

      {/* Agent lanes */}
      <div
        className="flex-1 overflow-y-auto"
        role="list"
        aria-label="Agent activity lanes"
      >
        {AGENT_NAMES.map((name) => (
          <AgentLane
            key={name}
            agentName={name}
            state={agents[name].state}
            lastWake={agents[name].lastWake}
            events={agents[name].events}
            eventRate={eventRates[name]}
          />
        ))}
      </div>
    </section>
  );
}
