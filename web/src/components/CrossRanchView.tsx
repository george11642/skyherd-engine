/**
 * CrossRanchView — /cross-ranch two-ranch handoff view.
 *
 * Two ranch-map canvases side by side with a shared fence indicator.
 * Handoff token animates A → B when a neighbor.handoff SSE event fires.
 * Below: timeline of last 10 handoffs.
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { RanchMap } from "./RanchMap";
import { getSSE } from "@/lib/sse";
import { cn } from "@/lib/cn";

interface NeighborHandoffEvent {
  from_ranch: string;
  to_ranch: string;
  species: string;
  shared_fence: string;
  response_mode: string;
  tool_calls: string[];
  rancher_paged: boolean;
  ts: number;
  latency_ms?: number;
  attest_hash?: string;
}

interface CrossRanchState {
  lastHandoff: NeighborHandoffEvent | null;
  ranchAActive: boolean;
  ranchBActive: boolean;
  sharedFenceAlert: boolean;
  handoffHistory: NeighborHandoffEvent[];
}

function useNeighborHandoff(): CrossRanchState {
  const [state, setState] = useState<CrossRanchState>({
    lastHandoff: null,
    ranchAActive: false,
    ranchBActive: false,
    sharedFenceAlert: false,
    handoffHistory: [],
  });
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleHandoff = useCallback((payload: NeighborHandoffEvent) => {
    setState((prev) => ({
      lastHandoff: payload,
      ranchAActive: true,
      ranchBActive: true,
      sharedFenceAlert: true,
      handoffHistory: [payload, ...prev.handoffHistory].slice(0, 10),
    }));

    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => {
      setState((prev) => ({
        ...prev,
        ranchAActive: false,
        ranchBActive: false,
        sharedFenceAlert: false,
      }));
    }, 8000);
  }, []);

  useEffect(() => {
    const sse = getSSE();
    sse.on("neighbor.handoff", handleHandoff);
    return () => {
      sse.off("neighbor.handoff", handleHandoff);
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [handleHandoff]);

  return state;
}

function formatTime(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function shortHash(h?: string): string {
  if (!h) return "—";
  return h.slice(0, 8) + "…";
}

export default function CrossRanchView() {
  const { lastHandoff, ranchAActive, ranchBActive, sharedFenceAlert, handoffHistory } =
    useNeighborHandoff();

  return (
    <div
      className="flex flex-col min-h-screen"
      style={{ backgroundColor: "var(--color-bg-0)" }}
    >
      {/* Header */}
      <header
        className="flex items-center justify-between px-4 py-3 shrink-0 border-b"
        style={{ backgroundColor: "var(--color-bg-1)", borderColor: "var(--color-line)" }}
      >
        <div className="flex items-center gap-3">
          <a
            href="/"
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "1.125rem",
              fontWeight: 600,
              letterSpacing: "-0.02em",
              color: "var(--color-text-0)",
              textDecoration: "none",
            }}
          >
            Sky<span style={{ color: "var(--color-accent-sage)" }}>Herd</span>
          </a>
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "0.6875rem",
              color: "var(--color-text-2)",
              letterSpacing: "0.04em",
            }}
          >
            CROSS-RANCH MESH
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="chip chip-muted">
            {handoffHistory.length} handoffs
          </span>
          {sharedFenceAlert && (
            <span className="chip chip-thermal">
              <span className="h-1.5 w-1.5 rounded-full bg-[rgb(255_143_60)] pulse-dot" aria-hidden="true" />
              ACTIVE
            </span>
          )}
        </div>
      </header>

      <div className="flex-1 flex flex-col gap-3 p-3">
        {/* Handoff banner */}
        <AnimatePresence>
          {lastHandoff && sharedFenceAlert && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.24 }}
              className="rounded border px-3 py-2"
              style={{
                backgroundColor: "rgb(255 143 60 / 0.08)",
                borderColor: "rgb(255 143 60 / 0.4)",
                fontFamily: "var(--font-mono)",
                fontSize: "0.6875rem",
              }}
              role="status"
              aria-live="polite"
            >
              <div className="flex flex-wrap gap-x-4 gap-y-1">
                {[
                  ["event",   "neighbor.handoff"],
                  ["from",    lastHandoff.from_ranch],
                  ["to",      lastHandoff.to_ranch],
                  ["species", lastHandoff.species],
                  ["fence",   lastHandoff.shared_fence],
                  ["mode",    lastHandoff.response_mode],
                  ["paged",   lastHandoff.rancher_paged ? "yes" : "no"],
                  ["ts",      formatTime(lastHandoff.ts)],
                ].map(([k, v]) => (
                  <span key={k}>
                    <span style={{ color: "var(--color-accent-thermal)" }}>{k}</span>{" "}
                    <span style={{ color: "var(--color-text-1)" }}>{v}</span>
                  </span>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Two-up ranch maps */}
        <div className="flex gap-0 flex-1 min-h-0" style={{ minHeight: "300px" }}>
          {/* Ranch A */}
          <div className="flex flex-col flex-1 min-w-0 gap-1">
            <div className="flex items-center justify-between px-1">
              <span
                className="tabnum"
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.625rem",
                  letterSpacing: "0.06em",
                  color: ranchAActive ? "var(--color-accent-dust)" : "var(--color-text-2)",
                }}
              >
                RANCH A · MESA VERDE
              </span>
              {ranchAActive && (
                <span className="chip chip-dust">
                  <span className="h-1.5 w-1.5 rounded-full bg-[rgb(210_178_138)] pulse-dot" aria-hidden="true" />
                  ALERT
                </span>
              )}
            </div>
            <div
              className={cn(
                "flex-1 rounded-l border transition-all duration-500 overflow-hidden",
                ranchAActive ? "fence-pulse" : "",
              )}
              style={{
                borderColor: ranchAActive ? "rgb(210 178 138 / 0.6)" : "var(--color-line)",
              }}
            >
              <RanchMap />
            </div>
          </div>

          {/* Shared fence indicator */}
          <div className="flex flex-col items-center justify-center w-8 shrink-0 gap-2">
            {/* Animated handoff token */}
            <div className="flex-1 flex flex-col items-center justify-center relative" style={{ minHeight: "60px" }}>
              <div
                className="w-px flex-1 transition-colors duration-500"
                style={{
                  backgroundColor: sharedFenceAlert
                    ? "var(--color-accent-thermal)"
                    : "var(--color-line)",
                  boxShadow: sharedFenceAlert
                    ? "0 0 8px 2px rgb(255 143 60 / 0.5)"
                    : "none",
                }}
                aria-hidden="true"
              />
              {/* Handoff token dot */}
              <AnimatePresence>
                {sharedFenceAlert && (
                  <motion.div
                    key="token"
                    initial={{ y: -20, opacity: 0 }}
                    animate={{ y: 20, opacity: 1 }}
                    exit={{ y: 40, opacity: 0 }}
                    transition={{ duration: 1.2, ease: "easeInOut" }}
                    className="absolute w-2.5 h-2.5 rounded-full"
                    style={{
                      backgroundColor: "var(--color-accent-thermal)",
                      boxShadow: "0 0 8px 3px rgb(255 143 60 / 0.6)",
                    }}
                    aria-hidden="true"
                  />
                )}
              </AnimatePresence>
            </div>
            {sharedFenceAlert && (
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.5rem",
                  color: "var(--color-accent-thermal)",
                  writingMode: "vertical-rl",
                  textTransform: "uppercase",
                  letterSpacing: "0.1em",
                }}
              >
                {lastHandoff?.shared_fence ?? "shared"}
              </span>
            )}
          </div>

          {/* Ranch B */}
          <div className="flex flex-col flex-1 min-w-0 gap-1">
            <div className="flex items-center justify-between px-1">
              <span
                className="tabnum"
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.625rem",
                  letterSpacing: "0.06em",
                  color: ranchBActive ? "var(--color-accent-sky)" : "var(--color-text-2)",
                }}
              >
                RANCH B · MESA DEL SOL
              </span>
              {ranchBActive && (
                <span className="chip chip-sky">
                  <span className="h-1.5 w-1.5 rounded-full bg-[rgb(120_180_220)] pulse-dot" aria-hidden="true" />
                  PRE-POSITION
                </span>
              )}
            </div>
            <div
              className={cn(
                "flex-1 rounded-r border transition-all duration-500 overflow-hidden",
              )}
              style={{
                borderColor: ranchBActive ? "rgb(120 180 220 / 0.6)" : "var(--color-line)",
                boxShadow: ranchBActive ? "0 0 8px 2px rgb(120 180 220 / 0.25)" : "none",
              }}
            >
              <RanchMap />
            </div>
          </div>
        </div>

        {/* Handoff timeline */}
        <section
          className="shrink-0 rounded border"
          style={{ backgroundColor: "var(--color-bg-1)", borderColor: "var(--color-line)" }}
          aria-label="Handoff timeline"
        >
          <div
            className="px-3 py-2 border-b flex items-center justify-between"
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
              Handoff Timeline
            </span>
            <span className="chip chip-muted">last 10</span>
          </div>

          <div className="overflow-x-auto">
            <table
              className="w-full text-left border-collapse"
              style={{ fontFamily: "var(--font-mono)", fontSize: "0.6875rem" }}
              aria-label="Cross-ranch handoff events"
            >
              <thead>
                <tr style={{ borderBottom: `1px solid var(--color-line)` }}>
                  {["TIME", "FROM", "TO", "SPECIES", "LATENCY", "HASH"].map((h) => (
                    <th
                      key={h}
                      className="px-3 py-1 font-medium"
                      style={{
                        color: "var(--color-text-2)",
                        fontSize: "0.5625rem",
                        letterSpacing: "0.06em",
                        backgroundColor: "var(--color-bg-1)",
                        position: "sticky",
                        top: 0,
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {handoffHistory.length === 0 ? (
                  <tr>
                    <td
                      colSpan={6}
                      className="px-3 py-4 text-center italic"
                      style={{ color: "var(--color-text-2)" }}
                    >
                      no handoff events yet
                    </td>
                  </tr>
                ) : (
                  handoffHistory.map((h, idx) => (
                    <tr
                      key={idx}
                      style={{ borderBottom: `1px solid var(--color-line)` }}
                      className="hover:bg-[var(--color-bg-2)] transition-colors"
                    >
                      <td className="px-3 py-1.5 tabnum whitespace-nowrap" style={{ color: "var(--color-text-2)" }}>
                        {formatTime(h.ts)}
                      </td>
                      <td className="px-3 py-1.5" style={{ color: "var(--color-accent-dust)" }}>
                        {h.from_ranch}
                      </td>
                      <td className="px-3 py-1.5" style={{ color: "var(--color-accent-sky)" }}>
                        {h.to_ranch}
                      </td>
                      <td className="px-3 py-1.5" style={{ color: "var(--color-accent-thermal)" }}>
                        {h.species}
                      </td>
                      <td className="px-3 py-1.5 tabnum" style={{ color: "var(--color-text-1)" }}>
                        {h.latency_ms != null ? `${h.latency_ms}ms` : "—"}
                      </td>
                      <td className="px-3 py-1.5 tabnum" style={{ color: "var(--color-text-2)" }}>
                        {shortHash(h.attest_hash)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* Footer legend */}
        <div
          className="flex items-center gap-4 text-xs shrink-0"
          style={{ fontFamily: "var(--font-mono)", color: "var(--color-text-2)" }}
        >
          <span>
            <span style={{ color: "var(--color-accent-dust)" }}>■</span> Ranch A alert
          </span>
          <span>
            <span style={{ color: "var(--color-accent-sky)" }}>■</span> Ranch B pre-position
          </span>
          <span>
            <span style={{ color: "var(--color-accent-thermal)" }}>|</span> fence pulse
          </span>
          <span className="ml-auto">
            skyherd-demo play cross_ranch_coyote
          </span>
        </div>
      </div>
    </div>
  );
}
