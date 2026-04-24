/**
 * LaptopDroneControl — manual Mavic control from the dashboard (Phase 7.1 LDC-02).
 *
 * Hidden by default so judges don't accidentally mash EMERGENCY STOP. Enable
 * via window.__DRONE_MANUAL_ENABLED=true or the URL query param `?drone=1`.
 *
 * Dangerous actions (ARM, TAKEOFF, EMERGENCY STOP) require a 3-second
 * hold-to-fire. DISARM, RTL, LAND fire on click. All POST to /api/drone/*
 * with an X-Manual-Override-Token header (read from window.__DRONE_MANUAL_TOKEN
 * or props.token).
 *
 * Live state comes from /api/snapshot polling (1s) + drone.manual_override SSE.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { cn } from "@/lib/cn";
import { getSSE } from "@/lib/sse";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ManualAction = "arm" | "disarm" | "takeoff" | "rtl" | "land" | "estop";

interface ManualOverrideEvent {
  action: ManualAction;
  actor: string;
  ts: number;
  success: boolean;
  latency_ms: number;
  error?: string;
  best_effort?: boolean;
}

interface DroneSnapshot {
  lat?: number;
  lon?: number;
  alt_m?: number;
  state?: string;
  battery_pct?: number;
}

interface ActionLog {
  id: string;
  action: ManualAction;
  ts: number;
  latency_ms: number;
  success: boolean;
  error?: string;
}

type ButtonStatus = "idle" | "sending" | "ok" | "error";

interface LaptopDroneControlProps {
  collapsed?: boolean;
  onToggle?: () => void;
  /** Overrides window.__DRONE_MANUAL_TOKEN in tests and preview builds. */
  token?: string;
  /** Forces the panel visible — tests skip the window/URL gating. */
  forceEnabled?: boolean;
}

// Actions that require a 3s hold-to-fire before firing.
const HOLD_ACTIONS: ReadonlySet<ManualAction> = new Set([
  "arm",
  "takeoff",
  "estop",
]);
const HOLD_DURATION_MS = 3000;
const MAX_LOG_ENTRIES = 5;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

declare global {
  interface Window {
    __DRONE_MANUAL_ENABLED?: boolean;
    __DRONE_MANUAL_TOKEN?: string;
  }
}

export function isManualEnabled(): boolean {
  if (typeof window === "undefined") return false;
  if (window.__DRONE_MANUAL_ENABLED === true) return true;
  try {
    const params = new URLSearchParams(window.location.search);
    if (params.get("drone") === "1") return true;
  } catch {
    // URLSearchParams is missing only in ancient runtimes; fail closed.
  }
  return false;
}

function getActiveToken(prop?: string): string {
  if (prop !== undefined) return prop;
  if (typeof window !== "undefined" && window.__DRONE_MANUAL_TOKEN) {
    return window.__DRONE_MANUAL_TOKEN;
  }
  return "";
}

function formatAlt(state: DroneSnapshot | null): string {
  if (!state || typeof state.alt_m !== "number") return "—";
  return `${state.alt_m.toFixed(1)} m`;
}

function formatBattery(state: DroneSnapshot | null): string {
  if (!state || typeof state.battery_pct !== "number") return "—";
  return `${Math.round(state.battery_pct)}%`;
}

function gpsValid(state: DroneSnapshot | null): boolean {
  return Boolean(
    state &&
      typeof state.lat === "number" &&
      typeof state.lon === "number" &&
      (state.lat !== 0 || state.lon !== 0),
  );
}

function modeChipVariant(state: DroneSnapshot | null): string {
  const mode = (state?.state ?? "").toLowerCase();
  if (mode === "idle" || mode === "grounded") return "chip-muted";
  if (mode === "patrol" || mode === "investigating" || mode === "manual")
    return "chip-dust";
  return "chip-sage";
}

function batteryChipVariant(state: DroneSnapshot | null): string {
  const pct = state?.battery_pct;
  if (typeof pct !== "number") return "chip-muted";
  if (pct < 25) return "chip-danger";
  if (pct < 50) return "chip-warn";
  return "chip-sage";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function LaptopDroneControl({
  collapsed = false,
  onToggle,
  token,
  forceEnabled,
}: LaptopDroneControlProps) {
  const [enabled] = useState<boolean>(() =>
    forceEnabled === true ? true : isManualEnabled(),
  );
  const [drone, setDrone] = useState<DroneSnapshot | null>(null);
  const [actionLog, setActionLog] = useState<ActionLog[]>([]);
  const [buttonStatus, setButtonStatus] = useState<
    Record<ManualAction, ButtonStatus>
  >({
    arm: "idle",
    disarm: "idle",
    takeoff: "idle",
    rtl: "idle",
    land: "idle",
    estop: "idle",
  });
  const [buttonError, setButtonError] = useState<
    Record<ManualAction, string | null>
  >({
    arm: null,
    disarm: null,
    takeoff: null,
    rtl: null,
    land: null,
    estop: null,
  });
  const [holdProgress, setHoldProgress] = useState<
    Record<ManualAction, number>
  >({
    arm: 0,
    disarm: 0,
    takeoff: 0,
    rtl: 0,
    land: 0,
    estop: 0,
  });
  const holdTimers = useRef<Record<ManualAction, number | null>>({
    arm: null,
    disarm: null,
    takeoff: null,
    rtl: null,
    land: null,
    estop: null,
  });
  const [liveAnnouncement, setLiveAnnouncement] = useState<string>("");

  // Poll /api/snapshot every 1s for drone state.
  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    const fetchSnapshot = () => {
      fetch("/api/snapshot")
        .then((r) => r.json())
        .then((data: { drone?: DroneSnapshot }) => {
          if (cancelled) return;
          if (data?.drone) setDrone(data.drone);
        })
        .catch(() => {});
    };
    fetchSnapshot();
    const iv = window.setInterval(fetchSnapshot, 1000);
    return () => {
      cancelled = true;
      window.clearInterval(iv);
    };
  }, [enabled]);

  // Subscribe to drone.manual_override SSE events for the action log.
  useEffect(() => {
    if (!enabled) return;
    const sse = getSSE();
    const handler = (payload: unknown) => {
      const p = payload as ManualOverrideEvent;
      if (!p || !p.action) return;
      setActionLog((prev) => {
        const entry: ActionLog = {
          id: `${p.action}-${p.ts}`,
          action: p.action,
          ts: p.ts,
          latency_ms: p.latency_ms ?? 0,
          success: p.success,
          error: p.error,
        };
        return [entry, ...prev].slice(0, MAX_LOG_ENTRIES);
      });
    };
    sse.on("drone.manual_override", handler);
    return () => {
      sse.off("drone.manual_override", handler);
    };
  }, [enabled]);

  const fire = useCallback(
    async (action: ManualAction) => {
      const activeToken = getActiveToken(token);
      setButtonStatus((s) => ({ ...s, [action]: "sending" }));
      setButtonError((e) => ({ ...e, [action]: null }));
      try {
        const resp = await fetch(`/api/drone/${action}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Manual-Override-Token": activeToken,
          },
          body: JSON.stringify({}),
        });
        if (!resp.ok) {
          const detail = (await resp.json().catch(() => ({ detail: "" })))
            .detail as string | undefined;
          setButtonStatus((s) => ({ ...s, [action]: "error" }));
          setButtonError((e) => ({
            ...e,
            [action]: `${resp.status}: ${detail ?? "error"}`,
          }));
          setLiveAnnouncement(`${action} failed: ${resp.status}`);
        } else {
          setButtonStatus((s) => ({ ...s, [action]: "ok" }));
          setLiveAnnouncement(`${action} fired`);
          // Auto-clear status after 1.5s so the button returns to idle.
          window.setTimeout(() => {
            setButtonStatus((s) =>
              s[action] === "ok" ? { ...s, [action]: "idle" } : s,
            );
          }, 1500);
        }
      } catch (err) {
        setButtonStatus((s) => ({ ...s, [action]: "error" }));
        setButtonError((e) => ({
          ...e,
          [action]: err instanceof Error ? err.message : "network error",
        }));
      }
    },
    [token],
  );

  const startHold = useCallback(
    (action: ManualAction) => {
      if (!HOLD_ACTIONS.has(action)) {
        void fire(action);
        return;
      }
      // Guard against double-starts.
      if (holdTimers.current[action] != null) return;
      const start = performance.now();
      const tick = () => {
        const elapsed = performance.now() - start;
        const pct = Math.min(1, elapsed / HOLD_DURATION_MS);
        setHoldProgress((p) => ({ ...p, [action]: pct }));
        if (pct >= 1) {
          holdTimers.current[action] = null;
          setHoldProgress((p) => ({ ...p, [action]: 0 }));
          void fire(action);
          return;
        }
        holdTimers.current[action] = window.setTimeout(tick, 50);
      };
      tick();
    },
    [fire],
  );

  const cancelHold = useCallback((action: ManualAction) => {
    if (!HOLD_ACTIONS.has(action)) return;
    const t = holdTimers.current[action];
    if (t != null) {
      window.clearTimeout(t);
      holdTimers.current[action] = null;
    }
    setHoldProgress((p) => ({ ...p, [action]: 0 }));
  }, []);

  if (!enabled) {
    // Render a short stub so the tab label still has a body — judges who
    // stumble onto the tab see a safety explainer, not a blank surface.
    return (
      <section
        aria-label="Laptop drone control (disabled)"
        data-testid="laptop-drone-panel-disabled"
        className="shrink-0 rounded border flex flex-col overflow-hidden"
        style={{
          backgroundColor: "var(--color-bg-1)",
          borderColor: "var(--color-line)",
        }}
      >
        <div
          className="flex items-center justify-between px-3 py-2 shrink-0 border-b"
          style={{ borderColor: "var(--color-line)" }}
        >
          <button
            type="button"
            className="flex-1 flex items-center gap-2 text-left min-w-0"
            style={{ background: "transparent" }}
            onClick={onToggle}
            aria-expanded={!collapsed}
          >
            <span
              className="font-semibold leading-none"
              style={{
                fontFamily: "var(--font-display)",
                fontSize: "0.8125rem",
                letterSpacing: "-0.01em",
                color: "var(--color-text-0)",
              }}
            >
              Laptop Drone
            </span>
            <span className="chip chip-muted">disabled</span>
          </button>
        </div>
        <div
          className="px-3 py-3 text-xs"
          style={{ color: "var(--color-text-2)" }}
        >
          Manual drone control is disabled by default. Enable with{" "}
          <code>?drone=1</code> in the URL or{" "}
          <code>window.__DRONE_MANUAL_ENABLED = true</code>.
        </div>
      </section>
    );
  }

  const collapseStyle: React.CSSProperties = collapsed
    ? { maxHeight: "44px", overflow: "hidden" }
    : {};

  return (
    <section
      aria-label="Laptop drone control"
      data-testid="laptop-drone-panel"
      className="shrink-0 rounded border flex flex-col overflow-hidden transition-all duration-240"
      style={{
        ...collapseStyle,
        backgroundColor: "var(--color-bg-1)",
        borderColor: "var(--color-line)",
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-3 py-2 shrink-0 border-b"
        style={{ borderColor: "var(--color-line)" }}
      >
        <button
          type="button"
          className="flex-1 flex items-center gap-2 text-left min-w-0"
          style={{ background: "transparent" }}
          onClick={onToggle}
          aria-expanded={!collapsed}
          aria-controls="laptop-drone-body"
        >
          <span
            className="font-semibold leading-none"
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "0.8125rem",
              letterSpacing: "-0.01em",
              color: "var(--color-text-0)",
            }}
          >
            Laptop Drone
          </span>
          <span className="chip chip-dust">manual</span>
        </button>
      </div>

      {/* ARIA live region for screen-readers */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
        data-testid="laptop-drone-live"
      >
        {liveAnnouncement}
      </div>

      {!collapsed && (
        <div
          id="laptop-drone-body"
          className="flex flex-col gap-2 px-3 py-2 overflow-auto"
        >
          {/* State chip band */}
          <div
            className="flex flex-wrap gap-1.5"
            data-testid="laptop-drone-state-chips"
          >
            <span className={cn("chip tabnum", batteryChipVariant(drone))}>
              BAT {formatBattery(drone)}
            </span>
            <span
              className={cn(
                "chip tabnum",
                gpsValid(drone) ? "chip-sage" : "chip-muted",
              )}
              data-testid="chip-gps"
            >
              GPS {gpsValid(drone) ? "lock" : "—"}
            </span>
            <span className="chip chip-muted tabnum" data-testid="chip-alt">
              ALT {formatAlt(drone)}
            </span>
            <span
              className={cn("chip tabnum", modeChipVariant(drone))}
              data-testid="chip-mode"
            >
              MODE {drone?.state ?? "idle"}
            </span>
          </div>

          {/* Action grid */}
          <div
            className="grid grid-cols-2 gap-1.5"
            role="group"
            aria-label="Drone actions"
          >
            <DroneActionButton
              action="arm"
              label="ARM"
              holdRequired
              progress={holdProgress.arm}
              status={buttonStatus.arm}
              error={buttonError.arm}
              onStart={() => startHold("arm")}
              onCancel={() => cancelHold("arm")}
            />
            <DroneActionButton
              action="disarm"
              label="DISARM"
              holdRequired={false}
              progress={0}
              status={buttonStatus.disarm}
              error={buttonError.disarm}
              onStart={() => startHold("disarm")}
              onCancel={() => cancelHold("disarm")}
            />
            <DroneActionButton
              action="takeoff"
              label="TAKEOFF"
              holdRequired
              progress={holdProgress.takeoff}
              status={buttonStatus.takeoff}
              error={buttonError.takeoff}
              onStart={() => startHold("takeoff")}
              onCancel={() => cancelHold("takeoff")}
            />
            <DroneActionButton
              action="rtl"
              label="RTL"
              holdRequired={false}
              progress={0}
              status={buttonStatus.rtl}
              error={buttonError.rtl}
              onStart={() => startHold("rtl")}
              onCancel={() => cancelHold("rtl")}
            />
            <DroneActionButton
              action="land"
              label="LAND"
              holdRequired={false}
              progress={0}
              status={buttonStatus.land}
              error={buttonError.land}
              onStart={() => startHold("land")}
              onCancel={() => cancelHold("land")}
            />
            <DroneActionButton
              action="estop"
              label="EMERGENCY STOP"
              holdRequired
              danger
              progress={holdProgress.estop}
              status={buttonStatus.estop}
              error={buttonError.estop}
              onStart={() => startHold("estop")}
              onCancel={() => cancelHold("estop")}
            />
          </div>

          {/* Action log */}
          <div
            className="flex flex-col gap-1 mt-1 border-t pt-2"
            style={{ borderColor: "var(--color-line)" }}
            data-testid="laptop-drone-log"
          >
            <span
              className="uppercase"
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.5625rem",
                letterSpacing: "0.06em",
                color: "var(--color-text-2)",
              }}
            >
              Recent actions
            </span>
            {actionLog.length === 0 && (
              <span
                className="text-mono-xs"
                style={{
                  color: "var(--color-text-2)",
                  fontSize: "0.6875rem",
                }}
              >
                No actions yet.
              </span>
            )}
            {actionLog.map((entry) => (
              <div
                key={entry.id}
                className="flex items-center gap-2"
                data-testid={`log-row-${entry.action}`}
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.6875rem",
                  color: entry.success
                    ? "var(--color-text-1)"
                    : "var(--color-danger)",
                }}
              >
                <span className="chip chip-muted tabnum">
                  {new Date(entry.ts * 1000).toLocaleTimeString("en-US", {
                    hour12: false,
                  })}
                </span>
                <span className="uppercase">{entry.action}</span>
                <span className="tabnum" style={{ color: "var(--color-text-2)" }}>
                  {entry.latency_ms} ms
                </span>
                {!entry.success && entry.error && (
                  <span className="truncate" title={entry.error}>
                    {entry.error}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Subcomponents
// ---------------------------------------------------------------------------

interface DroneActionButtonProps {
  action: ManualAction;
  label: string;
  holdRequired: boolean;
  danger?: boolean;
  progress: number;
  status: ButtonStatus;
  error: string | null;
  onStart: () => void;
  onCancel: () => void;
}

function DroneActionButton({
  action,
  label,
  holdRequired,
  danger = false,
  progress,
  status,
  error,
  onStart,
  onCancel,
}: DroneActionButtonProps) {
  const ariaLabel = holdRequired
    ? `${label} — hold 3 seconds to fire`
    : `${label} — click to fire`;

  const baseClass = cn(
    "relative px-3 py-2 text-xs font-medium cursor-pointer",
    "transition-colors rounded border select-none",
    danger ? "chip-danger" : status === "ok" ? "chip-sage" : "chip-muted",
    status === "error" && "chip-danger",
  );

  return (
    <button
      type="button"
      data-testid={`drone-btn-${action}`}
      aria-label={ariaLabel}
      aria-describedby={error ? `drone-err-${action}` : undefined}
      className={baseClass}
      onPointerDown={(e) => {
        e.preventDefault();
        onStart();
      }}
      onPointerUp={onCancel}
      onPointerLeave={onCancel}
      onPointerCancel={onCancel}
      onKeyDown={(e) => {
        if (e.key === " " || e.key === "Enter") {
          e.preventDefault();
          if (!e.repeat) onStart();
        }
      }}
      onKeyUp={(e) => {
        if (e.key === " " || e.key === "Enter") {
          e.preventDefault();
          onCancel();
        }
      }}
      onClick={(e) => {
        // Non-hold actions fire on click; hold actions are driven by
        // onPointerDown above and we prevent the synthetic click.
        if (holdRequired) {
          e.preventDefault();
          return;
        }
      }}
      style={{
        minHeight: 40,
        fontFamily: "var(--font-mono)",
        letterSpacing: "0.04em",
      }}
    >
      <span className="relative z-10">
        {label}
        {status === "sending" && "…"}
      </span>
      {holdRequired && progress > 0 && (
        <span
          aria-hidden
          data-testid={`drone-progress-${action}`}
          className="absolute left-0 bottom-0 h-0.5"
          style={{
            width: `${progress * 100}%`,
            backgroundColor: danger
              ? "var(--color-danger)"
              : "var(--color-accent-sage)",
            transition: "width 50ms linear",
          }}
        />
      )}
      {error && (
        <span
          id={`drone-err-${action}`}
          className="sr-only"
          role="alert"
        >
          {error}
        </span>
      )}
    </button>
  );
}
