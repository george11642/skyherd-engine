/**
 * StatBand — the top 64px header bar with live status chips.
 */

import { useState, useEffect, useCallback } from "react";
import { motion, useSpring, useTransform } from "framer-motion";
import { Chip } from "./Chip";
import { getSSE } from "@/lib/sse";
import { getAudio } from "@/lib/audio";

/**
 * AnimatedCount — 400ms tween across an integer/float value.
 * Reuses the spring stiffness from CostTicker.AnimatedCost so chip
 * transitions stay visually consistent across the dashboard.
 */
function AnimatedCount({ value, format }: { value: number; format: (v: number) => string }) {
  const spring = useSpring(value, { stiffness: 60, damping: 20, duration: 0.4 });
  const display = useTransform(spring, (v) => format(v));
  useEffect(() => {
    spring.set(value);
  }, [value, spring]);
  return <motion.span className="tabnum">{display}</motion.span>;
}

interface BandStats {
  meshSessions: number;
  busTopics: number;
  ledgerEvents: number;
  costPerDay: number;
  uptime: string;
  allIdle: boolean;
}

function formatUptime(startTs: number): string {
  const secs = Math.floor((Date.now() / 1000) - startTs);
  const d = Math.floor(secs / 86400);
  const h = Math.floor((secs % 86400) / 3600);
  if (d > 0) return `${d}d ${h}h`;
  const m = Math.floor((secs % 3600) / 60);
  return `${h}h ${m}m`;
}

export function StatBand() {
  const [muted, setMuted] = useState(() => getAudio().isMuted());

  const toggleMute = useCallback(() => {
    const next = !muted;
    getAudio().setMuted(next);
    setMuted(next);
  }, [muted]);

  const [stats, setStats] = useState<BandStats>({
    meshSessions: 0,
    busTopics: 7,
    ledgerEvents: 0,
    costPerDay: 0,
    uptime: "—",
    allIdle: true,
  });

  const [startTs] = useState(() => Math.floor(Date.now() / 1000) - 3600 * 9 - 60 * 4);

  const handleCostTick = useCallback((payload: {
    agents?: Array<{ state: string }>;
    total_cumulative_usd?: number;
    all_idle?: boolean;
    rate_per_hr_usd?: number;
  }) => {
    const active = payload.agents?.filter((a) => a.state === "active").length ?? 0;
    const costDay = (payload.rate_per_hr_usd ?? 0) * 24;
    setStats((prev) => ({
      ...prev,
      meshSessions: active,
      costPerDay: costDay,
      allIdle: payload.all_idle ?? true,
    }));
  }, []);

  const handleAttest = useCallback((entry: { seq?: number }) => {
    if (typeof entry.seq === "number") {
      const seq = entry.seq;
      setStats((prev) => ({ ...prev, ledgerEvents: seq + 1 }));
    }
  }, []);

  useEffect(() => {
    const sse = getSSE();
    sse.on("cost.tick", handleCostTick);
    sse.on("attest.append", handleAttest);
    fetch("/api/attest")
      .then((r) => r.json())
      .then((d) => {
        if (Array.isArray(d.entries) && d.entries.length > 0) {
          const last = d.entries[d.entries.length - 1];
          setStats((prev) => ({ ...prev, ledgerEvents: last.seq + 1 }));
        }
      })
      .catch(() => {});
    return () => {
      sse.off("cost.tick", handleCostTick);
      sse.off("attest.append", handleAttest);
    };
  }, [handleCostTick, handleAttest]);

  useEffect(() => {
    const tick = () =>
      setStats((prev) => ({ ...prev, uptime: formatUptime(startTs) }));
    tick();
    const id = setInterval(tick, 60_000);
    return () => clearInterval(id);
  }, [startTs]);

  return (
    <header
      className="flex items-center justify-between px-4 shrink-0 border-b"
      style={{
        height: "64px",
        backgroundColor: "var(--color-bg-1)",
        borderColor: "var(--color-line)",
      }}
      role="banner"
    >
      {/* Wordmark */}
      <div className="flex items-center gap-3 shrink-0">
        <a
          href="/"
          className="flex items-center gap-2 no-underline"
          aria-label="SkyHerd — return to dashboard"
        >
          <span
            className="font-semibold leading-none"
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "1.375rem",
              letterSpacing: "-0.02em",
              color: "var(--color-text-0)",
            }}
          >
            Sky<span style={{ color: "var(--color-accent-sage)" }}>Herd</span>
          </span>
        </a>
        <span
          className="hidden sm:inline tabnum"
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.6875rem",
            color: "var(--color-text-2)",
            letterSpacing: "0.04em",
          }}
        >
          ranch_a · {(import.meta.env.VITE_DEMO_MODE === "replay" || (typeof window !== "undefined" && new URLSearchParams(window.location.search).get("replay"))) ? "replay" : "live"}
        </span>
      </div>

      {/* Status chips */}
      <nav
        className="flex items-center gap-2 flex-wrap justify-end"
        aria-label="System status"
      >
        <Chip variant="sage" dot pulse={!stats.allIdle}>
          MESH:{" "}
          <AnimatedCount
            value={stats.meshSessions}
            format={(v) => `${Math.round(v)} sessions`}
          />
        </Chip>
        <Chip variant="sky" dot>
          BUS: {stats.busTopics} topics
        </Chip>
        <Chip variant="muted" dot>
          LEDGER:{" "}
          <AnimatedCount
            value={stats.ledgerEvents}
            format={(v) => `${Math.round(v).toLocaleString()} events`}
          />
        </Chip>
        <Chip variant={stats.allIdle ? "muted" : "dust"} dot pulse={!stats.allIdle}>
          COST: $
          <AnimatedCount
            value={stats.costPerDay || 0.17}
            format={(v) => `${v.toFixed(2)}/day`}
          />
        </Chip>
        <Chip variant="muted">
          UPTIME: {stats.uptime}
        </Chip>

        <button
          type="button"
          onClick={toggleMute}
          aria-pressed={muted}
          aria-label={muted ? "Unmute audio" : "Mute audio"}
          title={muted ? "Unmute" : "Mute"}
          className="chip chip-muted cursor-pointer transition-opacity hover:opacity-80 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent-sage)]"
        >
          {muted ? (
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/>
            </svg>
          ) : (
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/>
            </svg>
          )}
        </button>

        <div
          className="hidden md:flex items-center gap-3 ml-3 pl-3"
          style={{ borderLeft: "1px solid var(--color-line)" }}
        >
          <a
            href="/"
            className="text-xs font-medium transition-colors"
            style={{ color: "var(--color-accent-sage)", fontFamily: "var(--font-body)" }}
            aria-current="page"
          >
            Dashboard
          </a>
          <a
            href="/rancher"
            className="text-xs font-medium transition-colors hover:opacity-80"
            style={{ color: "var(--color-text-2)", fontFamily: "var(--font-body)" }}
          >
            Rancher
          </a>
          <a
            href="/cross-ranch"
            className="text-xs font-medium transition-colors hover:opacity-80"
            style={{ color: "var(--color-text-2)", fontFamily: "var(--font-body)" }}
          >
            Cross-Ranch
          </a>
        </div>
      </nav>
    </header>
  );
}
