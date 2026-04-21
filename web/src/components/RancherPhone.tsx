/**
 * RancherPhone — /rancher PWA view.
 *
 * Shows:
 * - Wes cowboy persona call screen (animated phone ring)
 * - Drone thermal feed area
 * - Live agent reasoning panel (last 20 events across all agents)
 */

import { useState, useEffect, useCallback } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import { getSSE } from "@/lib/sse";

interface AgentLogEntry {
  ts: number;
  agent: string;
  message: string;
  state?: string;
  level?: string;
}

interface CallState {
  active: boolean;
  urgency: "normal" | "high" | "critical";
  message: string;
  agent?: string;
}

const URGENCY_COLORS = {
  normal: "text-green-400",
  high: "text-yellow-400",
  critical: "text-red-400",
};

const URGENCY_BADGE: Record<string, "success" | "warning" | "destructive"> = {
  normal: "success",
  high: "warning",
  critical: "destructive",
};

function formatTime(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export function RancherPhone() {
  const [logs, setLogs] = useState<AgentLogEntry[]>([]);
  const [call, setCall] = useState<CallState | null>(null);
  const [droneState, setDroneState] = useState("idle");
  const [cowCount, setCowCount] = useState<number | null>(null);

  const handleLog = useCallback((payload: AgentLogEntry) => {
    setLogs((prev) => [...prev, payload].slice(-20));

    // Trigger call screen on critical events
    if (
      payload.message.toLowerCase().includes("calving") ||
      payload.message.toLowerCase().includes("coyote") ||
      payload.message.toLowerCase().includes("priority") ||
      payload.message.toLowerCase().includes("wes call")
    ) {
      setCall({
        active: true,
        urgency: payload.message.toLowerCase().includes("priority") ? "critical" : "high",
        message: payload.message,
        agent: payload.agent,
      });
      // Auto-dismiss after 8s
      setTimeout(() => setCall(null), 8000);
    }
  }, []);

  const handleSnapshot = useCallback((payload: {
    drone?: { state?: string };
    cows?: unknown[];
  }) => {
    if (payload.drone?.state) setDroneState(payload.drone.state);
    if (Array.isArray(payload.cows)) setCowCount(payload.cows.length);
  }, []);

  useEffect(() => {
    const sse = getSSE();
    sse.on("agent.log", handleLog);
    sse.on("world.snapshot", handleSnapshot);
    return () => {
      sse.off("agent.log", handleLog);
      sse.off("world.snapshot", handleSnapshot);
    };
  }, [handleLog, handleSnapshot]);

  return (
    <div className="min-h-screen bg-slate-950 p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">SkyHerd</h1>
          <p className="text-xs text-slate-500">Ranch Intelligence — Rancher View</p>
        </div>
        <div className="flex gap-2">
          {cowCount !== null && (
            <Badge variant="success">{cowCount} cattle</Badge>
          )}
          <Badge variant={droneState === "idle" ? "muted" : "default"}>
            Drone: {droneState}
          </Badge>
        </div>
      </div>

      {/* Call screen (conditional) */}
      {call && (
        <div
          className={cn(
            "rounded-2xl border p-6 text-center space-y-4",
            call.urgency === "critical"
              ? "border-red-500/60 bg-red-500/10"
              : "border-yellow-500/60 bg-yellow-500/10",
          )}
          role="alert"
          aria-live="assertive"
        >
          {/* Animated phone */}
          <div className="flex justify-center">
            <span className="text-5xl phone-ring" role="img" aria-label="Incoming call">
              📞
            </span>
          </div>
          <div>
            <p className="text-lg font-bold text-slate-100">Wes calling…</p>
            <p className="text-sm text-slate-400 mt-1">{call.agent}</p>
          </div>
          <p className={cn("text-sm font-mono", URGENCY_COLORS[call.urgency])}>
            {call.message}
          </p>
          <div className="flex gap-3 justify-center">
            <Button
              variant="default"
              className="bg-green-600 hover:bg-green-700 border-green-700"
              onClick={() => setCall(null)}
            >
              Answer
            </Button>
            <Button variant="outline" onClick={() => setCall(null)}>
              Dismiss
            </Button>
          </div>
        </div>
      )}

      {/* Drone feed area */}
      <Card>
        <CardHeader>
          <CardTitle>Drone Feed</CardTitle>
          <Badge variant={droneState !== "idle" ? "success" : "muted"}>
            {droneState}
          </Badge>
        </CardHeader>
        <CardContent>
          <div
            className="rounded-lg bg-slate-900 border border-slate-700 h-40 flex items-center justify-center"
            role="img"
            aria-label="Drone thermal feed placeholder"
          >
            <div className="text-center space-y-2">
              <div className="text-4xl opacity-20">🚁</div>
              <p className="text-xs text-slate-600 font-mono">
                {droneState === "idle"
                  ? "Drone grounded — no active mission"
                  : `Live thermal feed · ${droneState.toUpperCase()}`}
              </p>
              {droneState !== "idle" && (
                <div className="flex gap-1 justify-center">
                  {Array.from({ length: 5 }, (_, i) => (
                    <span
                      key={i}
                      className="h-1 w-6 rounded bg-green-400"
                      style={{ opacity: 0.3 + i * 0.14 }}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Agent reasoning panel */}
      <Card>
        <CardHeader>
          <CardTitle>Agent Reasoning</CardTitle>
          <span className="text-xs text-slate-500">Last 20 events</span>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y divide-slate-700/30 max-h-72 overflow-y-auto">
            {logs.length === 0 ? (
              <p className="px-4 py-3 text-xs text-slate-600 italic">
                Waiting for agent events…
              </p>
            ) : (
              logs
                .slice()
                .reverse()
                .map((log, idx) => (
                  <div key={idx} className="px-4 py-2 flex gap-3 items-start">
                    <span className="text-xs text-slate-600 font-mono shrink-0">
                      {formatTime(log.ts)}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex gap-2 items-center mb-0.5">
                        <span className="text-xs font-semibold text-slate-400 truncate">
                          {log.agent}
                        </span>
                        {log.state && (
                          <Badge
                            variant={log.state === "active" ? "success" : "muted"}
                            className="text-xs py-0"
                          >
                            {log.state}
                          </Badge>
                        )}
                      </div>
                      <p
                        className={cn(
                          "text-xs text-slate-300 leading-relaxed",
                          log.level === "ERROR" && "text-red-400",
                        )}
                      >
                        {log.message}
                      </p>
                    </div>
                  </div>
                ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
