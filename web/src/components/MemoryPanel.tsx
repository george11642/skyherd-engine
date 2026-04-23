/**
 * MemoryPanel — judge-visible per-agent memory feed.
 *
 * Mirrors AttestationPanel structure: 5-tab switcher, memver HashChip rows,
 * flash animation on memory.written SSE, MAX_ENTRIES=50 with dedupe-by-memver.
 *
 * Phase 01 Plan 06.
 */

import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/cn";
import { getSSE } from "@/lib/sse";
import { HashChip } from "@/components/shared/HashChip";

const AGENTS = [
  "FenceLineDispatcher",
  "HerdHealthWatcher",
  "PredatorPatternLearner",
  "GrazingOptimizer",
  "CalvingWatch",
] as const;

type AgentName = (typeof AGENTS)[number];

interface MemoryEntry {
  memory_id: string;
  memory_version_id: string;
  memory_store_id: string;
  path: string;
  content_sha256: string;
  content_size_bytes: number;
  created_at: string;
  operation?: "created" | "updated" | "deleted" | "redacted";
  created_by?: { type: string; api_key_id: string };
}

interface MemoryWrittenPayload {
  agent: string;
  memory_store_id: string;
  memory_id: string;
  memory_version_id: string;
  content_sha256: string;
  path: string;
}

const MAX_ENTRIES = 50;

export interface MemoryPanelProps {
  collapsed?: boolean;
  onToggle?: () => void;
}

export function MemoryPanel({ collapsed = false, onToggle }: MemoryPanelProps) {
  const [activeAgent, setActiveAgent] = useState<AgentName>(AGENTS[0]);
  const [entriesByAgent, setEntriesByAgent] = useState<Record<string, MemoryEntry[]>>({});
  const [flashingIds, setFlashingIds] = useState<Set<string>>(new Set());

  const handleWrite = useCallback((payload: unknown) => {
    const p = payload as MemoryWrittenPayload;
    if (!p?.agent || !p?.memory_version_id) return;
    const entry: MemoryEntry = {
      memory_id: p.memory_id,
      memory_version_id: p.memory_version_id,
      memory_store_id: p.memory_store_id,
      path: p.path,
      content_sha256: p.content_sha256,
      content_size_bytes: 0,
      created_at: new Date().toISOString(),
      operation: "created",
      created_by: { type: "api_actor", api_key_id: "live" },
    };
    setEntriesByAgent((prev) => {
      const existing = prev[p.agent] ?? [];
      const deduped = [
        entry,
        ...existing.filter((e) => e.memory_version_id !== entry.memory_version_id),
      ];
      return { ...prev, [p.agent]: deduped.slice(0, MAX_ENTRIES) };
    });
    setFlashingIds((prev) => new Set(prev).add(entry.memory_version_id));
    setTimeout(() => {
      setFlashingIds((prev) => {
        const n = new Set(prev);
        n.delete(entry.memory_version_id);
        return n;
      });
    }, 800);
  }, []);

  useEffect(() => {
    const sse = getSSE();
    sse.on("memory.written", handleWrite);
    fetch(`/api/memory/${activeAgent}`)
      .then((r) => r.json())
      .then((data: { entries?: MemoryEntry[] }) => {
        if (Array.isArray(data.entries)) {
          setEntriesByAgent((prev) => ({
            ...prev,
            [activeAgent]: data.entries!.slice(0, MAX_ENTRIES),
          }));
        }
      })
      .catch(() => {});
    return () => {
      sse.off("memory.written", handleWrite);
    };
  }, [activeAgent, handleWrite]);

  const entries = entriesByAgent[activeAgent] ?? [];

  const collapseStyle: React.CSSProperties = collapsed
    ? { maxHeight: "44px", overflow: "hidden" }
    : { maxHeight: "220px" };

  return (
    <section
      aria-label="Memory panel"
      data-testid="memory-panel"
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
          aria-controls="memory-body"
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
            Memory
          </span>
          <span className="chip chip-muted tabnum">{entries.length} entries</span>
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

      {/* Tabs */}
      <div
        className="flex items-center gap-1 px-3 py-1.5 shrink-0 border-b overflow-x-auto"
        role="tablist"
        style={{ borderColor: "var(--color-line)" }}
      >
        {AGENTS.map((name) => (
          <button
            key={name}
            role="tab"
            aria-selected={activeAgent === name}
            onClick={() => setActiveAgent(name)}
            data-testid={`memory-tab-${name}`}
            className={cn(
              "chip tabnum whitespace-nowrap",
              activeAgent === name ? "chip-sage" : "chip-muted",
            )}
            style={{ cursor: "pointer" }}
          >
            {name}
          </button>
        ))}
      </div>

      {/* Feed */}
      {!collapsed && (
        <div id="memory-body" className="flex-1 overflow-auto">
          <table className="w-full text-left border-collapse text-mono-xs" aria-label="Memory chain">
            <thead>
              <tr style={{ borderBottom: `1px solid var(--color-line)` }}>
                {["OP", "PATH", "MEMVER"].map((h) => (
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
                <tr style={{ borderBottom: `1px solid var(--color-line)` }}>
                  <td
                    colSpan={3}
                    className="px-3 py-3 text-center"
                    style={{ color: "var(--color-text-2)" }}
                  >
                    No memory entries yet
                  </td>
                </tr>
              )}
              {entries.map((v) => (
                <tr
                  key={v.memory_version_id}
                  data-testid="memory-row"
                  className={cn(
                    "transition-colors",
                    flashingIds.has(v.memory_version_id) && "memory-row--flash",
                  )}
                  style={{
                    borderBottom: `1px solid var(--color-line)`,
                    backgroundColor: flashingIds.has(v.memory_version_id)
                      ? "var(--color-accent-sage-bg, rgba(134, 196, 148, 0.18))"
                      : undefined,
                  }}
                >
                  <td className="px-3 py-1">
                    <span className="chip chip-sky">{v.operation ?? "created"}</span>
                  </td>
                  <td
                    className="px-3 py-1 truncate"
                    style={{ color: "var(--color-text-1)", maxWidth: "14rem" }}
                    title={v.path}
                  >
                    {v.path}
                  </td>
                  <td className="px-3 py-1" style={{ color: "var(--color-text-2)" }}>
                    <HashChip hash={v.memory_version_id} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
