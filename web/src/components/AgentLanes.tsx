/**
 * AgentLanes — stacks all 5 SkyHerd agent log lanes, wired to SSE.
 */

import { useState, useEffect, useCallback } from "react";
import { AgentLane, type AgentEvent } from "@/components/AgentLane";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { getSSE } from "@/lib/sse";

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

export function AgentLanes() {
  const [agents, setAgents] = useState<Record<AgentName, AgentState>>(makeInitialState);

  const handleLog = useCallback((payload: {
    agent: string;
    message: string;
    ts: number;
    state?: string;
    level?: string;
  }) => {
    const name = payload.agent as AgentName;
    if (!AGENT_NAMES.includes(name)) return;

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
          lastWake:
            payload.state === "active" ? payload.ts : existing.lastWake,
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
          next[name] = {
            ...next[name],
            state: a.state as AgentState["state"],
          };
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

  return (
    <Card className="flex flex-col overflow-hidden h-full">
      <CardHeader>
        <CardTitle>Agent Activity</CardTitle>
        <span className="text-xs text-slate-500">5 Managed Agents</span>
      </CardHeader>
      <div className="flex-1 overflow-y-auto divide-y divide-slate-700/40">
        {AGENT_NAMES.map((name) => (
          <AgentLane
            key={name}
            agentName={name}
            state={agents[name].state}
            lastWake={agents[name].lastWake}
            events={agents[name].events}
          />
        ))}
      </div>
    </Card>
  );
}
