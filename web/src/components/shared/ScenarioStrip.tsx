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
          className="pointer-events-none absolute inset-x-0 bottom-0 z-20 flex items-end justify-center"
          style={{ height: "180px" }}
          data-testid="start-simulation-overlay"
        >
          <button
            type="button"
            onClick={handleStart}
            aria-pressed={!replay.isPaused()}
            aria-label="Start Simulation — begins the 5-scenario demo replay"
            className={cn(
              "btn btn-primary pointer-events-auto scenario-active",
              "pointer-events-auto flex flex-col items-center gap-1",
              "px-6 py-3 text-sm font-semibold",
              "focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent-sage)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--color-bg-0)]",
            )}
          >
            <span>Start Simulation</span>
            <span className="text-[0.6875rem] font-normal opacity-80">
              ~10 min · 5 scenarios, no backend required
            </span>
          </button>
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
