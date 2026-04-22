/**
 * CrossRanchView — side-by-side ranch map canvases for the cross-ranch mesh demo.
 *
 * Renders Ranch A (Mesa Verde Ranch) and Ranch B (Mesa del Sol Ranch) next to
 * each other. When a neighbor.handoff SSE event arrives, the shared fence on
 * both canvases pulses and the pre-position drone icon appears on Ranch B.
 *
 * Entry point: /?view=cross-ranch
 *
 * Uses the existing RanchMap component; this file only wires the two-up layout
 * and the SSE neighbor.handoff subscription.
 */

import { useEffect, useRef, useState } from "react";
import RanchMap from "./RanchMap";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface NeighborHandoffEvent {
  from_ranch: string;
  to_ranch: string;
  species: string;
  shared_fence: string;
  response_mode: string;
  tool_calls: string[];
  rancher_paged: boolean;
  ts: number;
}

interface CrossRanchState {
  lastHandoff: NeighborHandoffEvent | null;
  ranchAActive: boolean;
  ranchBActive: boolean;
  sharedFenceAlert: boolean;
}

// ---------------------------------------------------------------------------
// Hook: subscribe to neighbor.handoff SSE events
// ---------------------------------------------------------------------------

function useNeighborHandoff(sseUrl: string): CrossRanchState {
  const [state, setState] = useState<CrossRanchState>({
    lastHandoff: null,
    ranchAActive: false,
    ranchBActive: false,
    sharedFenceAlert: false,
  });

  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const es = new EventSource(sseUrl);

    es.addEventListener("neighbor.handoff", (e: MessageEvent) => {
      try {
        const payload: NeighborHandoffEvent = JSON.parse(e.data);
        setState({
          lastHandoff: payload,
          ranchAActive: true,
          ranchBActive: true,
          sharedFenceAlert: true,
        });

        // Clear the visual alert after 8 seconds
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
        timeoutRef.current = setTimeout(() => {
          setState((prev) => ({
            ...prev,
            ranchAActive: false,
            ranchBActive: false,
            sharedFenceAlert: false,
          }));
        }, 8000);
      } catch {
        // malformed payload — ignore
      }
    });

    return () => {
      es.close();
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [sseUrl]);

  return state;
}

// ---------------------------------------------------------------------------
// SharedFenceIndicator — pulsing divider between the two maps
// ---------------------------------------------------------------------------

function SharedFenceIndicator({
  active,
  label,
}: {
  active: boolean;
  label: string;
}) {
  return (
    <div
      className={[
        "flex flex-col items-center justify-center w-10 shrink-0 gap-1",
        "transition-all duration-500",
      ].join(" ")}
    >
      <div
        className={[
          "w-1 flex-1 rounded-full transition-all duration-500",
          active
            ? "bg-amber-400 shadow-[0_0_12px_3px_rgba(251,191,36,0.7)]"
            : "bg-neutral-600",
        ].join(" ")}
      />
      {active && (
        <span className="text-[9px] text-amber-300 font-mono text-center leading-tight px-1 whitespace-nowrap">
          {label}
        </span>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// HandoffBanner — status strip shown when a handoff fires
// ---------------------------------------------------------------------------

function HandoffBanner({ handoff }: { handoff: NeighborHandoffEvent }) {
  const ts = new Date(handoff.ts * 1000).toISOString().slice(11, 19);
  return (
    <div className="bg-amber-900/80 border border-amber-500 rounded px-3 py-2 text-xs font-mono text-amber-200 flex flex-wrap gap-x-4 gap-y-1">
      <span>
        <span className="text-amber-400">event</span> neighbor.handoff
      </span>
      <span>
        <span className="text-amber-400">from</span> {handoff.from_ranch}
      </span>
      <span>
        <span className="text-amber-400">to</span> {handoff.to_ranch}
      </span>
      <span>
        <span className="text-amber-400">species</span> {handoff.species}
      </span>
      <span>
        <span className="text-amber-400">fence</span> {handoff.shared_fence}
      </span>
      <span>
        <span className="text-amber-400">mode</span> {handoff.response_mode}
      </span>
      <span>
        <span className="text-amber-400">tools</span>{" "}
        {handoff.tool_calls.join(", ")}
      </span>
      <span>
        <span className="text-amber-400">rancher_paged</span>{" "}
        {handoff.rancher_paged ? "yes" : "no (silent handoff)"}
      </span>
      <span>
        <span className="text-amber-400">ts</span> {ts}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// CrossRanchView
// ---------------------------------------------------------------------------

interface CrossRanchViewProps {
  /** SSE stream URL; defaults to /api/events */
  sseUrl?: string;
}

export default function CrossRanchView({
  sseUrl = "/api/events",
}: CrossRanchViewProps) {
  const { lastHandoff, ranchAActive, ranchBActive, sharedFenceAlert } =
    useNeighborHandoff(sseUrl);

  return (
    <div className="flex flex-col gap-3 p-4 bg-neutral-950 min-h-screen">
      {/* Header */}
      <div className="flex items-center gap-3">
        <h1 className="text-sm font-semibold text-neutral-200 font-mono uppercase tracking-widest">
          Cross-Ranch Mesh
        </h1>
        <span className="text-xs text-neutral-500 font-mono">
          agent-to-agent choreography · silent handoff · one protocol · two
          sessions
        </span>
      </div>

      {/* Handoff banner */}
      {lastHandoff && <HandoffBanner handoff={lastHandoff} />}

      {/* Two-up ranch maps */}
      <div className="flex flex-row gap-0 flex-1 min-h-0">
        {/* Ranch A */}
        <div className="flex flex-col flex-1 min-w-0 gap-1">
          <span
            className={[
              "text-[10px] font-mono uppercase tracking-wider px-1",
              ranchAActive ? "text-amber-300" : "text-neutral-400",
            ].join(" ")}
          >
            Ranch A · Mesa Verde Ranch
            {ranchAActive && (
              <span className="ml-2 text-amber-400">● ACTIVE</span>
            )}
          </span>
          <div
            className={[
              "flex-1 rounded-l border transition-all duration-500",
              ranchAActive
                ? "border-amber-500/60 shadow-[0_0_8px_2px_rgba(251,191,36,0.25)]"
                : "border-neutral-700",
            ].join(" ")}
          >
            <RanchMap />
          </div>
        </div>

        {/* Shared fence indicator */}
        <SharedFenceIndicator
          active={sharedFenceAlert}
          label={lastHandoff?.shared_fence ?? "shared fence"}
        />

        {/* Ranch B */}
        <div className="flex flex-col flex-1 min-w-0 gap-1">
          <span
            className={[
              "text-[10px] font-mono uppercase tracking-wider px-1",
              ranchBActive ? "text-sky-300" : "text-neutral-400",
            ].join(" ")}
          >
            Ranch B · Mesa del Sol Ranch
            {ranchBActive && (
              <span className="ml-2 text-sky-400">
                ● PRE-POSITIONING
              </span>
            )}
          </span>
          <div
            className={[
              "flex-1 rounded-r border transition-all duration-500",
              ranchBActive
                ? "border-sky-500/60 shadow-[0_0_8px_2px_rgba(56,189,248,0.25)]"
                : "border-neutral-700",
            ].join(" ")}
          >
            <RanchMap />
          </div>
        </div>
      </div>

      {/* Footer legend */}
      <div className="flex gap-4 text-[10px] font-mono text-neutral-500">
        <span>
          <span className="text-amber-400">■</span> Ranch A alert
        </span>
        <span>
          <span className="text-sky-400">■</span> Ranch B pre-position
        </span>
        <span>
          <span className="text-amber-400">|</span> shared fence pulse
        </span>
        <span className="ml-auto">
          CLI: skyherd-demo play cross_ranch_coyote
        </span>
      </div>
    </div>
  );
}
