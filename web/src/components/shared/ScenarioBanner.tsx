import { useState, useEffect, useCallback } from "react";
import { getSSE } from "@/lib/sse";

type BannerState =
  | { phase: "idle" }
  | { phase: "active"; name: string; headline: string; color: ChipColor }
  | { phase: "attested"; name: string; color: ChipColor };

type ChipColor = "thermal" | "warn" | "sky" | "dust" | "sage" | "muted";

const SCENARIO_META: Record<
  string,
  { headline: string; color: ChipColor }
> = {
  coyote: {
    headline: "Coyote detected — NE fence · FenceLineDispatcher dispatching drone",
    color: "thermal",
  },
  sick_cow: {
    headline: "Cow flagged — HerdHealthWatcher drafting vet intake",
    color: "warn",
  },
  water_drop: {
    headline: "Tank level low · Drone flyover dispatched",
    color: "sky",
  },
  calving: {
    headline: "Pre-labor signal · CalvingWatch paging rancher",
    color: "dust",
  },
  storm: {
    headline: "Storm inbound · GrazingOptimizer moving herd",
    color: "warn",
  },
};

function getBorderColor(color: ChipColor): string {
  switch (color) {
    case "thermal": return "var(--color-accent-thermal)";
    case "warn":    return "var(--color-warn)";
    case "sky":     return "var(--color-accent-sky)";
    case "dust":    return "var(--color-accent-dust)";
    case "sage":    return "var(--color-accent-sage)";
    default:        return "var(--color-line)";
  }
}

function getMeta(name: string): { headline: string; color: ChipColor } {
  return (
    SCENARIO_META[name] ?? {
      headline: `Scenario: ${name}`,
      color: "muted" as ChipColor,
    }
  );
}

export function ScenarioBanner() {
  const [state, setState] = useState<BannerState>({ phase: "idle" });

  const handleActive = useCallback((payload: { name?: string }) => {
    if (typeof payload?.name !== "string") return;
    const meta = getMeta(payload.name);
    setState({ phase: "active", name: payload.name, ...meta });
  }, []);

  const handleEnded = useCallback((payload: { name?: string }) => {
    const name = typeof payload?.name === "string" ? payload.name : "";
    const meta = getMeta(name);
    setState({ phase: "attested", name, color: meta.color });
    setTimeout(() => {
      setState({ phase: "idle" });
    }, 2000);
  }, []);

  useEffect(() => {
    const sse = getSSE();
    sse.on("scenario.active", handleActive);
    sse.on("scenario.ended", handleEnded);
    return () => {
      sse.off("scenario.active", handleActive);
      sse.off("scenario.ended", handleEnded);
    };
  }, [handleActive, handleEnded]);

  const borderColor =
    state.phase === "idle"
      ? "var(--color-line)"
      : getBorderColor(state.color);

  return (
    <div
      className="flex items-center gap-2 px-3 shrink-0"
      style={{
        height: "44px",
        backgroundColor: "var(--color-bg-1)",
        borderBottom: `1px solid ${borderColor}`,
        transition: "border-color 0.4s ease",
      }}
      role="status"
      aria-live="polite"
      aria-label="Active scenario status"
      data-testid="scenario-banner"
    >
      {state.phase === "idle" && (
        <span
          className="font-mono text-[0.6875rem] tracking-wider"
          style={{ color: "var(--color-text-2)" }}
          data-testid="banner-idle"
        >
          Standing by…
        </span>
      )}

      {state.phase === "active" && (
        <>
          <span
            aria-hidden="true"
            style={{ color: getBorderColor(state.color), fontSize: "0.875rem" }}
          >
            ⚠
          </span>
          <span
            className={`chip chip-${state.color}`}
            style={{ borderColor: getBorderColor(state.color) }}
          >
            LIVE
          </span>
          <span
            className="font-mono text-[0.6875rem] truncate"
            style={{ color: "var(--color-text-1)" }}
            data-testid="banner-headline"
          >
            {state.headline}
          </span>
        </>
      )}

      {state.phase === "attested" && (
        <>
          <span
            aria-hidden="true"
            style={{ color: "var(--color-ok)", fontSize: "0.875rem" }}
          >
            ✓
          </span>
          <span
            className="font-mono text-[0.6875rem] truncate"
            style={{ color: "var(--color-text-1)" }}
            data-testid="banner-headline"
          >
            {state.name} · attested
          </span>
        </>
      )}
    </div>
  );
}
