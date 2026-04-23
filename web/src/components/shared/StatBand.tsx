/**
 * StatBand — the top 64px header bar with live status chips.
 */

import { useState, useEffect, useCallback } from "react";
import { motion, useSpring, useTransform } from "framer-motion";
import { Chip } from "./Chip";
import { getSSE } from "@/lib/sse";

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
          ranch_a · {import.meta.env.VITE_DEMO_MODE === "replay" ? "replay" : "live"}
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
