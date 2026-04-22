/**
 * ScenarioStrip — 8 scenario pill markers.
 * Active scenario outlined in its color. Click toggles active state.
 */

import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/cn";
import { getSSE } from "@/lib/sse";

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

export function ScenarioStrip() {
  const [active, setActive] = useState<ScenarioId | null>(null);

  const handleLog = useCallback((payload: { message?: string }) => {
    const msg = (payload.message ?? "").toLowerCase();
    for (const s of SCENARIOS) {
      if (msg.includes(s.id.replace("_", " ")) || msg.includes(s.id)) {
        setActive(s.id);
        return;
      }
    }
  }, []);

  useEffect(() => {
    const sse = getSSE();
    sse.on("agent.log", handleLog);
    return () => sse.off("agent.log", handleLog);
  }, [handleLog]);

  return (
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
                ? `chip-${s.color}`
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
  );
}
