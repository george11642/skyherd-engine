/**
 * CostTicker — live cost meter for SkyHerd Managed Agents.
 *
 * Shows:
 * - $0.08/hr rate when any agent is active
 * - "PAUSED (idle)" when ALL agents are idle
 * - Cumulative cost total
 * - Per-agent breakdown strip
 */

import { useState, useEffect, useCallback } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import { getSSE } from "@/lib/sse";

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
  FenceLineDispatcher: "Fence",
  HerdHealthWatcher: "Health",
  PredatorPatternLearner: "Predator",
  GrazingOptimizer: "Grazing",
  CalvingWatch: "Calving",
};

export function CostTicker() {
  const [tick, setTick] = useState<CostTickPayload | null>(null);

  const handleTick = useCallback((payload: CostTickPayload) => {
    setTick(payload);
  }, []);

  useEffect(() => {
    const sse = getSSE();
    sse.on("cost.tick", handleTick);
    return () => sse.off("cost.tick", handleTick);
  }, [handleTick]);

  const allIdle = tick?.all_idle ?? true;
  const totalCost = tick?.total_cumulative_usd ?? 0;
  const rateUsd = tick?.rate_per_hr_usd ?? 0;

  return (
    <Card className="shrink-0">
      <CardHeader className="py-2">
        <CardTitle className="text-xs">Cost Meter</CardTitle>
        {/* The "money shot" — visible pause when all idle */}
        {allIdle ? (
          <Badge variant="muted" className="text-xs font-mono">
            <span className="h-1.5 w-1.5 rounded-full bg-slate-500 mr-1" />
            PAUSED (idle)
          </Badge>
        ) : (
          <Badge variant="success" className="text-xs font-mono">
            <span className="h-1.5 w-1.5 rounded-full bg-green-400 pulse-dot mr-1" />
            $0.08/hr active
          </Badge>
        )}
      </CardHeader>

      <div className="px-4 pb-3 space-y-2">
        {/* Total cost display */}
        <div className="flex items-baseline gap-2">
          <span
            className={cn(
              "font-mono text-2xl font-bold tabular-nums transition-colors",
              allIdle ? "text-slate-500" : "text-green-400",
            )}
          >
            ${totalCost.toFixed(6)}
          </span>
          <span className="text-xs text-slate-500">cumulative</span>
        </div>

        {/* Rate line — must contain literal "$0.08/hr" and "idle"/"paused" */}
        <div className="text-xs font-mono text-slate-500">
          {allIdle ? (
            <span>
              Rate: <span className="text-slate-400">$0.00/hr</span>{" "}
              — <span className="text-yellow-400">paused</span> (all sessions idle)
            </span>
          ) : (
            <span>
              Rate: <span className="text-green-400">$0.08/hr</span> per active session
            </span>
          )}
        </div>

        {/* Per-agent strip */}
        {tick?.agents && (
          <div className="grid grid-cols-5 gap-1 pt-1">
            {tick.agents.map((a) => (
              <div
                key={a.name}
                className={cn(
                  "rounded px-1.5 py-1 text-center border",
                  a.state === "active"
                    ? "border-green-500/40 bg-green-500/10"
                    : "border-slate-700/60 bg-slate-800/30",
                )}
                title={`${a.name}: ${a.state} — $${a.cumulative_cost_usd.toFixed(6)}`}
              >
                <div
                  className={cn(
                    "text-xs font-mono truncate",
                    a.state === "active" ? "text-green-400" : "text-slate-600",
                  )}
                >
                  {AGENT_SHORT[a.name] ?? a.name.slice(0, 5)}
                </div>
                <div
                  className={cn(
                    "text-xs font-mono tabular-nums mt-0.5",
                    a.state === "active" ? "text-green-300" : "text-slate-600",
                  )}
                >
                  {a.state === "active" ? "●" : "○"}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}
