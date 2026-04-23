/**
 * CrossRanchPanel — judge-visible cross-ranch neighbor handoff feed.
 *
 * Mirrors MemoryPanel layout: collapsible header, inbound+outbound tables
 * with flash animation on new entries via neighbor.alert / neighbor.handoff
 * SSE events.
 *
 * Phase 02 CRM-04 + CRM-05 + CRM-06.
 */

import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/cn";
import { getSSE } from "@/lib/sse";

type Direction = "inbound" | "outbound";

interface NeighborEntry {
  direction: Direction;
  from_ranch: string;
  to_ranch: string;
  species: string;
  shared_fence: string;
  confidence: number;
  ts: number;
  attestation_hash?: string;
}

const MAX_ENTRIES = 50;

export interface CrossRanchPanelProps {
  collapsed?: boolean;
  onToggle?: () => void;
}

function keyFor(e: NeighborEntry): string {
  return `${e.direction}|${e.from_ranch}|${e.to_ranch}|${e.shared_fence}|${e.ts}`;
}

export function CrossRanchPanel({
  collapsed = false,
  onToggle,
}: CrossRanchPanelProps) {
  const [entries, setEntries] = useState<NeighborEntry[]>([]);
  const [flashingKeys, setFlashingKeys] = useState<Set<string>>(new Set());

  const handleIncoming = useCallback(
    (payload: unknown, direction: Direction) => {
      const p = payload as Partial<NeighborEntry>;
      if (!p?.from_ranch || !p?.to_ranch) return;
      const entry: NeighborEntry = {
        direction,
        from_ranch: p.from_ranch,
        to_ranch: p.to_ranch,
        species: p.species ?? "unknown",
        shared_fence: p.shared_fence ?? "unknown",
        confidence: typeof p.confidence === "number" ? p.confidence : 0,
        ts: typeof p.ts === "number" ? p.ts : 0,
        attestation_hash: p.attestation_hash,
      };
      const k = keyFor(entry);
      setEntries((prev) => {
        const deduped = [entry, ...prev.filter((e) => keyFor(e) !== k)];
        return deduped.slice(0, MAX_ENTRIES);
      });
      setFlashingKeys((prev) => new Set(prev).add(k));
      setTimeout(() => {
        setFlashingKeys((prev) => {
          const n = new Set(prev);
          n.delete(k);
          return n;
        });
      }, 800);
    },
    [],
  );

  const handleAlert = useCallback(
    (payload: unknown) => handleIncoming(payload, "inbound"),
    [handleIncoming],
  );
  const handleHandoff = useCallback(
    (payload: unknown) => handleIncoming(payload, "outbound"),
    [handleIncoming],
  );

  useEffect(() => {
    const sse = getSSE();
    sse.on("neighbor.alert", handleAlert);
    sse.on("neighbor.handoff", handleHandoff);

    fetch("/api/neighbors")
      .then((r) => r.json())
      .then((data: { entries?: NeighborEntry[] }) => {
        if (Array.isArray(data.entries)) {
          setEntries(data.entries.slice(0, MAX_ENTRIES));
        }
      })
      .catch(() => {});

    return () => {
      sse.off("neighbor.alert", handleAlert);
      sse.off("neighbor.handoff", handleHandoff);
    };
  }, [handleAlert, handleHandoff]);

  const inbound = entries.filter((e) => e.direction === "inbound");
  const outbound = entries.filter((e) => e.direction === "outbound");

  const collapseStyle: React.CSSProperties = collapsed
    ? { maxHeight: "44px", overflow: "hidden" }
    : { maxHeight: "220px" };

  const renderRow = (e: NeighborEntry) => {
    const k = keyFor(e);
    const flashing = flashingKeys.has(k);
    return (
      <tr
        key={k}
        data-testid="neighbor-row"
        className={cn("transition-colors", flashing && "memory-row--flash")}
        style={{
          borderBottom: "1px solid var(--color-line)",
          backgroundColor: flashing
            ? "var(--color-accent-sage-bg, rgba(134, 196, 148, 0.18))"
            : undefined,
        }}
      >
        <td className="px-3 py-1" style={{ color: "var(--color-text-1)" }}>
          <span className="chip chip-sky">{e.from_ranch}</span>
          <span style={{ opacity: 0.5, margin: "0 .25rem" }}>→</span>
          <span className="chip chip-muted">{e.to_ranch}</span>
        </td>
        <td className="px-3 py-1" style={{ color: "var(--color-text-1)" }}>
          {e.species}
        </td>
        <td className="px-3 py-1 tabnum" style={{ color: "var(--color-text-2)" }}>
          {e.shared_fence}
        </td>
        <td className="px-3 py-1 tabnum" style={{ color: "var(--color-text-2)" }}>
          {(e.confidence * 100).toFixed(0)}%
        </td>
      </tr>
    );
  };

  const renderTable = (
    label: string,
    testId: string,
    rows: NeighborEntry[],
  ) => (
    <div className="flex-1 min-w-0 overflow-auto">
      <div
        className="px-3 py-1 font-medium"
        style={{
          color: "var(--color-text-2)",
          letterSpacing: "0.06em",
          fontSize: "0.5625rem",
          textTransform: "uppercase",
          position: "sticky",
          top: 0,
          backgroundColor: "var(--color-bg-1)",
          borderBottom: "1px solid var(--color-line)",
        }}
      >
        {label} ({rows.length})
      </div>
      <table
        className="w-full text-left border-collapse text-mono-xs"
        aria-label={`${label} neighbor events`}
        data-testid={testId}
      >
        <tbody>
          {rows.length === 0 && (
            <tr>
              <td
                colSpan={4}
                className="px-3 py-3 text-center"
                style={{ color: "var(--color-text-2)" }}
              >
                No {label.toLowerCase()} alerts yet
              </td>
            </tr>
          )}
          {rows.map(renderRow)}
        </tbody>
      </table>
    </div>
  );

  return (
    <section
      aria-label="Cross-ranch neighbor panel"
      data-testid="cross-ranch-panel"
      className="shrink-0 rounded border flex flex-col overflow-hidden transition-all duration-240"
      style={{
        ...collapseStyle,
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
          aria-controls="cross-ranch-body"
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
            Cross-Ranch Mesh
          </span>
          <span className="chip chip-muted tabnum">
            {inbound.length} in / {outbound.length} out
          </span>
        </button>
        <span
          aria-hidden
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.625rem",
            color: "var(--color-text-2)",
          }}
        >
          {collapsed ? "▲" : "▼"}
        </span>
      </div>

      {!collapsed && (
        <div id="cross-ranch-body" className="flex-1 flex overflow-hidden">
          {renderTable("INBOUND", "cross-ranch-inbound", inbound)}
          <div style={{ borderLeft: "1px solid var(--color-line)" }} />
          {renderTable("OUTBOUND", "cross-ranch-outbound", outbound)}
        </div>
      )}
    </section>
  );
}
