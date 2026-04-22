/**
 * RancherPhone — /rancher PWA view.
 *
 * Dark phone-first. Shows Wes call screen when agents fire critical events,
 * drone thermal feed, and a live agent reasoning panel.
 */

import { useState, useEffect, useCallback } from "react";
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

function formatTime(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function formatRelative(ts: number): string {
  const diff = Math.floor(Date.now() / 1000 - ts);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

const URGENCY_COLOR: Record<string, string> = {
  normal:   "var(--color-accent-sage)",
  high:     "var(--color-warn)",
  critical: "var(--color-danger)",
};

const LEVEL_COLOR: Record<string, string> = {
  ERROR: "var(--color-danger)",
  WARN:  "var(--color-warn)",
  INFO:  "var(--color-text-1)",
};

export function RancherPhone() {
  const [logs, setLogs] = useState<AgentLogEntry[]>([]);
  const [call, setCall] = useState<CallState | null>(null);
  const [droneState, setDroneState] = useState("idle");
  const [cowCount, setCowCount] = useState<number | null>(null);
  const [lastEventTs, setLastEventTs] = useState<number | null>(null);

  const handleLog = useCallback((payload: AgentLogEntry) => {
    setLogs((prev) => [...prev, payload].slice(-20));
    setLastEventTs(payload.ts);

    const msg = payload.message.toLowerCase();
    if (
      msg.includes("calving") ||
      msg.includes("coyote") ||
      msg.includes("priority") ||
      msg.includes("wes call") ||
      msg.includes("sick") ||
      msg.includes("breach")
    ) {
      setCall({
        active: true,
        urgency: msg.includes("priority") || msg.includes("critical") ? "critical" : "high",
        message: payload.message,
        agent: payload.agent,
      });
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

  const droneActive = droneState !== "idle";

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{
        backgroundColor: "var(--color-bg-0)",
        paddingTop: "env(safe-area-inset-top)",
        paddingBottom: "env(safe-area-inset-bottom)",
        paddingLeft: "env(safe-area-inset-left)",
        paddingRight: "env(safe-area-inset-right)",
      }}
    >
      {/* Header */}
      <header
        className="flex items-center justify-between px-4 py-3 shrink-0 border-b"
        style={{ borderColor: "var(--color-line)", backgroundColor: "var(--color-bg-1)" }}
      >
        <div>
          <h1
            className="leading-none"
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "1.25rem",
              fontWeight: 600,
              letterSpacing: "-0.02em",
              color: "var(--color-text-0)",
            }}
          >
            Sky<span style={{ color: "var(--color-accent-sage)" }}>Herd</span>
          </h1>
          <p
            className="mt-0.5"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "0.6875rem",
              color: "var(--color-text-2)",
            }}
          >
            Rancher View · {import.meta.env.VITE_DEMO_MODE === "replay" ? "replay" : "live"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {cowCount !== null && (
            <span className="chip chip-sage">{cowCount} cattle</span>
          )}
          <span className={cn("chip", droneActive ? "chip-sky" : "chip-muted")}>
            <span
              className={cn("h-1.5 w-1.5 rounded-full shrink-0", droneActive ? "bg-[rgb(120_180_220)] pulse-dot" : "bg-[rgb(38_45_58)]")}
              aria-hidden="true"
            />
            {droneState.toUpperCase()}
          </span>
        </div>
      </header>

      <div className="flex-1 flex flex-col gap-3 p-4">
        {/* ── Call screen ── */}
        {call ? (
          <div
            className="rounded border p-5 flex flex-col items-center gap-4"
            style={{
              backgroundColor: `rgb(from ${call.urgency === "critical" ? "224 100 90" : "240 195 80"} r g b / 0.08)`,
              borderColor: URGENCY_COLOR[call.urgency],
            }}
            role="alert"
            aria-live="assertive"
          >
            {/* Caller ID */}
            <div className="flex flex-col items-center gap-3">
              <div
                className="h-16 w-16 rounded-full flex items-center justify-center phone-ring"
                style={{ backgroundColor: "rgb(148 176 136 / 0.15)", border: "2px solid var(--color-accent-sage)" }}
                aria-label="Incoming call from Wes"
              >
                <span
                  style={{
                    fontFamily: "var(--font-display)",
                    fontSize: "1.75rem",
                    fontWeight: 700,
                    color: "var(--color-accent-sage)",
                    letterSpacing: "-0.02em",
                  }}
                >
                  W
                </span>
              </div>
              <div className="text-center">
                <p
                  style={{
                    fontFamily: "var(--font-display)",
                    fontSize: "1.25rem",
                    fontWeight: 600,
                    letterSpacing: "-0.02em",
                    color: "var(--color-text-0)",
                  }}
                >
                  Wes calling...
                </p>
                <p
                  className="mt-0.5"
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.6875rem",
                    color: "var(--color-text-2)",
                  }}
                >
                  {call.agent}
                </p>
              </div>
            </div>

            {/* Message */}
            <p
              className="text-center w-full"
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.8125rem",
                color: URGENCY_COLOR[call.urgency],
                lineHeight: 1.5,
              }}
            >
              {call.message}
            </p>

            {/* Action buttons */}
            <div className="flex flex-col gap-2 w-full">
              <button
                className="btn btn-primary w-full"
                onClick={() => setCall(null)}
                aria-label="Answer call"
              >
                Answer
              </button>
              <div className="flex gap-2">
                <button
                  className="btn btn-ghost flex-1"
                  onClick={() => setCall(null)}
                  aria-label="Dismiss call"
                >
                  Dismiss
                </button>
                <button
                  className="btn btn-ghost flex-1"
                  onClick={() => setCall(null)}
                  aria-label="Log only"
                >
                  Log only
                </button>
              </div>
            </div>
          </div>
        ) : (
          /* All-quiet state */
          <div
            className="rounded border px-4 py-3 flex items-center gap-3"
            style={{
              backgroundColor: "var(--color-bg-1)",
              borderColor: "var(--color-line)",
            }}
            role="status"
          >
            <span
              className="h-2 w-2 rounded-full shrink-0"
              style={{ backgroundColor: "var(--color-accent-sage)" }}
              aria-hidden="true"
            />
            <div>
              <p style={{ color: "var(--color-text-0)", fontSize: "0.875rem" }}>
                All quiet.
              </p>
              {lastEventTs && (
                <p
                  className="mt-0.5 tabnum"
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.6875rem",
                    color: "var(--color-text-2)",
                  }}
                >
                  Last event {formatRelative(lastEventTs)} · {formatTime(lastEventTs)}
                </p>
              )}
            </div>
          </div>
        )}

        {/* ── Drone feed ── */}
        <section
          className="rounded border"
          style={{
            backgroundColor: "var(--color-bg-1)",
            borderColor: droneActive ? "rgb(120 180 220 / 0.4)" : "var(--color-line)",
          }}
          aria-label="Drone feed"
        >
          <div
            className="flex items-center justify-between px-3 py-2 border-b"
            style={{ borderColor: "var(--color-line)" }}
          >
            <span
              style={{
                fontFamily: "var(--font-display)",
                fontSize: "0.8125rem",
                fontWeight: 600,
                letterSpacing: "-0.01em",
                color: "var(--color-text-0)",
              }}
            >
              Drone Feed
            </span>
            <span className={cn("chip", droneActive ? "chip-sky" : "chip-muted")}>
              {droneState.toUpperCase()}
            </span>
          </div>
          <div
            className="flex items-center justify-center"
            style={{ height: "9rem", backgroundColor: "var(--color-bg-0)" }}
            role="img"
            aria-label={droneActive ? `Live thermal feed — ${droneState}` : "Drone grounded"}
          >
            {droneActive ? (
              <div className="flex flex-col items-center gap-2">
                {/* Thermal scan lines */}
                <div className="flex gap-1">
                  {Array.from({ length: 8 }, (_, i) => (
                    <div
                      key={i}
                      className="w-5 rounded-sm"
                      style={{
                        height: `${8 + Math.sin(i * 1.3) * 6}px`,
                        backgroundColor: `rgb(255 143 60 / ${0.2 + i * 0.08})`,
                        transition: "height 200ms ease",
                      }}
                    />
                  ))}
                </div>
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.6875rem",
                    color: "var(--color-accent-thermal)",
                  }}
                >
                  THERMAL · {droneState.toUpperCase()}
                </span>
              </div>
            ) : (
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.6875rem",
                  color: "var(--color-text-2)",
                }}
              >
                drone grounded — no active mission
              </span>
            )}
          </div>
        </section>

        {/* ── Agent reasoning panel ── */}
        <section
          className="rounded border flex-1"
          style={{
            backgroundColor: "var(--color-bg-1)",
            borderColor: "var(--color-line)",
          }}
          aria-label="Agent reasoning"
        >
          <div
            className="flex items-center justify-between px-3 py-2 border-b"
            style={{ borderColor: "var(--color-line)" }}
          >
            <span
              style={{
                fontFamily: "var(--font-display)",
                fontSize: "0.8125rem",
                fontWeight: 600,
                letterSpacing: "-0.01em",
                color: "var(--color-text-0)",
              }}
            >
              Agent Reasoning
            </span>
            <span
              className="chip chip-muted"
              style={{ fontFamily: "var(--font-mono)" }}
            >
              last {logs.length} events
            </span>
          </div>

          <div
            className="divide-y overflow-y-auto"
            style={{
              maxHeight: "16rem",
            }}
            role="log"
            aria-label="Agent event log"
            aria-live="polite"
          >
            {logs.length === 0 ? (
              <p
                className="px-3 py-3 italic"
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.6875rem",
                  color: "var(--color-text-2)",
                }}
              >
                waiting for agent events
              </p>
            ) : (
              logs
                .slice()
                .reverse()
                .map((log, idx) => (
                  <div
                    key={idx}
                    className="px-3 py-2 flex gap-3 items-start"
                    style={{ borderColor: "var(--color-line)" }}
                  >
                    <span
                      className="tabnum shrink-0 mt-0.5"
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "0.6875rem",
                        color: "var(--color-text-2)",
                      }}
                    >
                      {formatTime(log.ts)}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span
                          className="text-xs font-medium truncate"
                          style={{ color: "var(--color-text-1)" }}
                        >
                          {log.agent}
                        </span>
                        {log.state && (
                          <span className={cn("chip", log.state === "active" ? "chip-sage" : "chip-muted")}>
                            {log.state}
                          </span>
                        )}
                      </div>
                      <p
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: "0.6875rem",
                          color: LEVEL_COLOR[log.level ?? "INFO"] ?? "var(--color-text-1)",
                          lineHeight: 1.5,
                        }}
                      >
                        {log.message}
                      </p>
                    </div>
                  </div>
                ))
            )}
          </div>
        </section>

        {/* Bottom nav */}
        <nav
          className="flex items-center justify-between pt-2"
          style={{ borderTop: "1px solid var(--color-line)" }}
          aria-label="App navigation"
        >
          <a
            href="/"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "0.6875rem",
              color: "var(--color-text-2)",
            }}
          >
            Dashboard
          </a>
          <a
            href="/cross-ranch"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "0.6875rem",
              color: "var(--color-text-2)",
            }}
          >
            Cross-Ranch
          </a>
        </nav>
      </div>
    </div>
  );
}
