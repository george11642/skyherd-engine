/**
 * ScenarioStrip — 8 scenario pill markers + opt-in "Start Simulation" overlay.
 * Active scenario outlined in its color. Click toggles active state.
 *
 * In replay/demo mode, a centered overlay CTA (Phase 3.3) appears above the
 * strip until the judge clicks Start. Dismissed locally once start() fires.
 */

import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/cn";
import { getSSE, getReplayIfActive } from "@/lib/sse";
import type { SkyHerdReplay } from "@/lib/replay";

/**
 * scenario.active / scenario.ended SSE contract (Part A, v1.1):
 *   scenario.active: { name: string, pass_idx: number, speed: number, started_at: string }
 *   scenario.ended:  { name: string, outcome: "passed" | "failed" }
 *
 * Until Part A ships these events this code path is inert — the handler never
 * fires so `active` stays driven by the legacy agent.log fuzzy match.
 */
interface ScenarioActivePayload {
  name?: string;
}

const SCENARIOS = [
  { id: "coyote",      label: "COYOTE",   color: "thermal" },
  { id: "sick_cow",    label: "SICK COW", color: "warn" },
  { id: "water_drop",  label: "WATER",    color: "sky" },
  { id: "calving",     label: "CALVING",  color: "dust" },
  { id: "storm",       label: "STORM",    color: "warn" },
  { id: "cross_ranch", label: "X-RANCH",  color: "sage" },
  { id: "wildfire",    label: "FIRE",     color: "thermal" },
  { id: "rustling",    label: "RUSTLING", color: "danger" },
] as const;

type ScenarioId = (typeof SCENARIOS)[number]["id"];

interface ScenarioStripProps {
  /** Test seam — injected replay instance. Defaults to module singleton. */
  replay?: SkyHerdReplay | null;
}

export function ScenarioStrip({ replay: replayProp }: ScenarioStripProps = {}) {
  const [active, setActive] = useState<ScenarioId | null>(null);
  // Resolved once on mount — avoids re-reading env on every render.
  const [replay] = useState<SkyHerdReplay | null>(() =>
    replayProp !== undefined ? replayProp : getReplayIfActive(),
  );
  const [overlayVisible, setOverlayVisible] = useState<boolean>(() =>
    replay !== null && replay.isPaused(),
  );
  const [announce, setAnnounce] = useState<string>("");

  const handleLog = useCallback((payload: { message?: string }) => {
    const msg = (payload.message ?? "").toLowerCase();
    for (const s of SCENARIOS) {
      if (msg.includes(s.id.replace("_", " ")) || msg.includes(s.id)) {
        setActive(s.id);
        return;
      }
    }
  }, []);

  const handleScenarioActive = useCallback((payload: ScenarioActivePayload) => {
    if (!payload || typeof payload.name !== "string") return;
    const match = SCENARIOS.find((s) => s.id === payload.name);
    if (match) setActive(match.id);
  }, []);

  const handleScenarioEnded = useCallback(() => {
    setActive(null);
  }, []);

  useEffect(() => {
    const sse = getSSE();
    sse.on("agent.log", handleLog);
    sse.on("scenario.active", handleScenarioActive);
    sse.on("scenario.ended", handleScenarioEnded);
    return () => {
      sse.off("agent.log", handleLog);
      sse.off("scenario.active", handleScenarioActive);
      sse.off("scenario.ended", handleScenarioEnded);
    };
  }, [handleLog, handleScenarioActive, handleScenarioEnded]);

  const handleStart = useCallback(() => {
    if (!replay) return;
    replay.start();
    setOverlayVisible(false);
    setAnnounce("Simulation started");
  }, [replay]);

  return (
    <div className="relative">
      {overlayVisible && replay !== null && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center"
          data-testid="start-simulation-overlay"
          style={{
            background: "radial-gradient(ellipse at center, rgba(10,12,16,0.72) 0%, rgba(10,12,16,0.94) 70%)",
            backdropFilter: "blur(6px)",
            WebkitBackdropFilter: "blur(6px)",
          }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="start-sim-title"
        >
          <div className="flex flex-col items-center gap-5 px-6 text-center">
            <div className="flex flex-col items-center gap-2">
              <span
                className="text-[0.6875rem] font-mono uppercase tracking-[0.22em]"
                style={{ color: "var(--color-accent-sage)" }}
              >
                simulation paused
              </span>
              <h2
                id="start-sim-title"
                className="max-w-xl text-4xl leading-tight tracking-tight sm:text-5xl"
                style={{
                  fontFamily: '"Fraunces Variable", Fraunces, serif',
                  color: "var(--color-text-1)",
                  fontVariationSettings: '"opsz" 72, "SOFT" 100',
                }}
              >
                SkyHerd is ready.
              </h2>
              <p
                className="max-w-md text-sm leading-relaxed"
                style={{ color: "var(--color-text-2)" }}
              >
                Click to run the 5-scenario demo — coyote, sick cow, water drop, calving, storm.
                All events are cryptographically attested in real time.
              </p>
            </div>

            <button
              type="button"
              onClick={handleStart}
              aria-pressed={!replay.isPaused()}
              aria-label="Start Simulation — begins the 5-scenario demo replay"
              className={cn(
                "group relative flex items-center gap-3 px-8 py-4",
                "rounded-full font-semibold tracking-wide",
                "transition-all duration-200",
                "focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-4",
              )}
              style={{
                background: "linear-gradient(180deg, var(--color-accent-sage) 0%, #7a9672 100%)",
                color: "#0a0c10",
                boxShadow:
                  "0 0 0 1px rgba(148,176,136,0.5), 0 8px 30px -6px rgba(148,176,136,0.55), 0 0 80px -10px rgba(148,176,136,0.45)",
                fontSize: "1.0625rem",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = "translateY(-1px)";
                e.currentTarget.style.boxShadow =
                  "0 0 0 1px rgba(148,176,136,0.7), 0 12px 40px -4px rgba(148,176,136,0.7), 0 0 100px -8px rgba(148,176,136,0.6)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "";
                e.currentTarget.style.boxShadow =
                  "0 0 0 1px rgba(148,176,136,0.5), 0 8px 30px -6px rgba(148,176,136,0.55), 0 0 80px -10px rgba(148,176,136,0.45)";
              }}
            >
              <svg
                className="scenario-active"
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="currentColor"
                aria-hidden="true"
              >
                <path d="M8 5v14l11-7z" />
              </svg>
              <span>Start Simulation</span>
            </button>

            <p
              className="font-mono text-[0.6875rem] tracking-wider"
              style={{ color: "var(--color-text-3, var(--color-text-2))", opacity: 0.7 }}
            >
              ~10 minutes · deterministic replay · no backend required
            </p>
          </div>
        </div>
      )}

      <div
        className="sr-only"
        role="status"
        aria-live="polite"
      >
        {announce}
      </div>

      <nav
        className="flex items-center gap-1 overflow-x-auto"
        aria-label="Active scenario"
      >
        {SCENARIOS.map((s) => {
          const isActive = active === s.id;
          return (
            <button
              key={s.id}
              className={cn(
                "chip shrink-0 cursor-pointer transition-all",
                isActive
                  ? `chip-${s.color} scenario-active`
                  : "border-[var(--color-line)] text-[var(--color-text-2)] hover:text-[var(--color-text-1)] hover:border-[var(--color-text-2)]",
              )}
              onClick={() => setActive(isActive ? null : s.id)}
              aria-pressed={isActive}
              aria-label={`Scenario: ${s.label}`}
            >
              {s.label}
            </button>
          );
        })}
      </nav>
    </div>
  );
}
