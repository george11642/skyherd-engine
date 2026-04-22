/**
 * AttestationPanel — tamper-evident Merkle chain ledger viewer.
 * Redesigned: dense mono rows, hover tooltip with full payload + signature.
 */

import { useState, useEffect, useCallback, Fragment } from "react";
import { cn } from "@/lib/cn";
import { getSSE } from "@/lib/sse";

interface LedgerEntry {
  seq: number;
  ts_iso: string;
  source: string;
  kind: string;
  payload_json: string;
  prev_hash: string;
  event_hash: string;
  signature: string;
  pubkey?: string;
}

type KindVariant = "sage" | "thermal" | "muted" | "sky" | "dust" | "warn" | "danger";

const KIND_CHIP: Record<string, KindVariant> = {
  "fence.breach": "thermal",
  "agent.wake":   "sage",
  "agent.sleep":  "muted",
  "cost.tick":    "muted",
  "sensor.reading": "sky",
  "neighbor.handoff": "dust",
};

function shortHash(h: string): string {
  if (!h || h.length < 12) return h ?? "—";
  return h.slice(0, 8) + "…" + h.slice(-4);
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  } catch {
    return iso;
  }
}

const MAX_ENTRIES = 50;

export interface AttestationPanelProps {
  collapsed?: boolean;
  onToggle?: () => void;
}

export function AttestationPanel({ collapsed = false, onToggle }: AttestationPanelProps) {
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [expanded, setExpanded] = useState<number | null>(null);

  const handleAppend = useCallback((entry: LedgerEntry) => {
    setEntries((prev) => [...prev, entry].slice(-MAX_ENTRIES));
  }, []);

  useEffect(() => {
    const sse = getSSE();
    sse.on("attest.append", handleAppend);
    fetch("/api/attest")
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data.entries)) {
          setEntries((prev) => {
            const combined = [...data.entries, ...prev];
            const seen = new Set<number>();
            return combined
              .filter((e) => {
                if (seen.has(e.seq)) return false;
                seen.add(e.seq);
                return true;
              })
              .sort((a, b) => a.seq - b.seq)
              .slice(-MAX_ENTRIES);
          });
        }
      })
      .catch(() => {});
    return () => sse.off("attest.append", handleAppend);
  }, [handleAppend]);

  const collapseStyle: React.CSSProperties = collapsed
    ? { maxHeight: "44px", overflow: "hidden" }
    : { maxHeight: "220px" };

  return (
    <section
      className="shrink-0 rounded border flex flex-col overflow-hidden transition-all duration-240"
      style={{
        ...collapseStyle,
        backgroundColor: "var(--color-bg-1)",
        borderColor: "var(--color-line)",
      }}
      aria-label="Attestation chain"
    >
      {/* Header */}
      <button
        className="flex items-center justify-between px-3 py-2 shrink-0 border-b w-full text-left"
        style={{ borderColor: "var(--color-line)", background: "transparent" }}
        onClick={onToggle}
        aria-expanded={!collapsed}
        aria-controls="attest-body"
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
          Attestation Chain
        </span>
        <div className="flex items-center gap-2">
          <span className="chip chip-muted tabnum">
            {entries.length} entries
          </span>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.625rem", color: "var(--color-text-2)" }}>
            {collapsed ? "▲" : "▼"}
          </span>
        </div>
      </button>

      {/* Table */}
      {!collapsed && (
        <div id="attest-body" className="flex-1 overflow-auto">
          <table
            className="w-full text-left border-collapse"
            style={{ fontFamily: "var(--font-mono)", fontSize: "0.6875rem" }}
          >
            <thead>
              <tr style={{ borderBottom: `1px solid var(--color-line)` }}>
                {["SEQ", "TIME", "SOURCE", "KIND", "HASH"].map((h) => (
                  <th
                    key={h}
                    className="px-3 py-1 font-medium tabnum"
                    style={{
                      color: "var(--color-text-2)",
                      position: "sticky",
                      top: 0,
                      backgroundColor: "var(--color-bg-1)",
                      letterSpacing: "0.06em",
                      fontSize: "0.5625rem",
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {entries.length === 0 && (
                <tr>
                  <td
                    colSpan={5}
                    className="px-3 py-4 text-center italic"
                    style={{ color: "var(--color-text-2)" }}
                  >
                    no ledger entries yet
                  </td>
                </tr>
              )}
              {entries.map((entry) => (
                <Fragment key={entry.seq}>
                  <tr
                    className={cn(
                      "cursor-pointer transition-colors",
                      expanded === entry.seq
                        ? "bg-[var(--color-bg-2)]"
                        : "hover:bg-[var(--color-bg-2)/50]",
                    )}
                    onClick={() => setExpanded(expanded === entry.seq ? null : entry.seq)}
                    aria-expanded={expanded === entry.seq}
                    style={{ borderBottom: `1px solid var(--color-line)` }}
                  >
                    <td className="px-3 py-1 tabnum" style={{ color: "var(--color-text-2)" }}>
                      {entry.seq}
                    </td>
                    <td className="px-3 py-1 tabnum whitespace-nowrap" style={{ color: "var(--color-text-2)" }}>
                      {formatTime(entry.ts_iso)}
                    </td>
                    <td
                      className="px-3 py-1 truncate max-w-[6rem]"
                      style={{ color: "var(--color-text-1)" }}
                      title={entry.source}
                    >
                      {entry.source}
                    </td>
                    <td className="px-3 py-1">
                      <span className={cn("chip", `chip-${KIND_CHIP[entry.kind] ?? "muted"}`)}>
                        {entry.kind}
                      </span>
                    </td>
                    <td className="px-3 py-1 tabnum" style={{ color: "var(--color-text-2)" }}>
                      {shortHash(entry.event_hash)}
                    </td>
                  </tr>
                  {expanded === entry.seq && (
                    <tr style={{ backgroundColor: "var(--color-bg-2)" }}>
                      <td colSpan={5} className="px-3 py-2">
                        <div className="space-y-1" style={{ fontSize: "0.6875rem" }}>
                          <div>
                            <span style={{ color: "var(--color-text-2)" }}>prev_hash: </span>
                            <span className="break-all" style={{ color: "var(--color-text-1)" }}>{entry.prev_hash}</span>
                          </div>
                          <div>
                            <span style={{ color: "var(--color-text-2)" }}>event_hash: </span>
                            <span className="break-all" style={{ color: "var(--color-text-0)" }}>{entry.event_hash}</span>
                          </div>
                          <div>
                            <span style={{ color: "var(--color-text-2)" }}>signature: </span>
                            <span className="break-all" style={{ color: "var(--color-accent-sky)" }}>{entry.signature}</span>
                          </div>
                          <div>
                            <span style={{ color: "var(--color-text-2)" }}>payload: </span>
                            <span className="break-all" style={{ color: "var(--color-accent-sage)" }}>{entry.payload_json}</span>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
