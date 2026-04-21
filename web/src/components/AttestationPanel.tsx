/**
 * AttestationPanel — tamper-evident Merkle chain ledger viewer.
 *
 * Lists last 50 entries. Click a row to expand and show payload + signature hex.
 * Collapsible as a bottom sheet.
 */

import { useState, useEffect, useCallback, Fragment } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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

const KIND_VARIANT: Record<string, "default" | "success" | "warning" | "destructive" | "muted"> = {
  "fence.breach": "destructive",
  "agent.wake": "success",
  "agent.sleep": "muted",
  "cost.tick": "outline" as unknown as "muted",
  "sensor.reading": "default",
};

function shortHash(h: string): string {
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
    setEntries((prev) => {
      const next = [...prev, entry].slice(-MAX_ENTRIES);
      return next;
    });
  }, []);

  useEffect(() => {
    const sse = getSSE();
    sse.on("attest.append", handleAppend);
    // Initial fetch
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
      .catch(() => {/* server may not be up in tests */});
    return () => sse.off("attest.append", handleAppend);
  }, [handleAppend]);

  return (
    <Card className="flex flex-col overflow-hidden shrink-0" style={{ maxHeight: collapsed ? "46px" : "220px" }}>
      <CardHeader className="py-2 cursor-pointer" onClick={onToggle}>
        <CardTitle className="text-xs">Attestation Chain</CardTitle>
        <div className="flex items-center gap-2">
          <Badge variant="default" className="text-xs font-mono">
            {entries.length} entries
          </Badge>
          <span className="text-slate-500 text-xs">{collapsed ? "▲ expand" : "▼ collapse"}</span>
        </div>
      </CardHeader>

      {!collapsed && (
        <div className="flex-1 overflow-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">Seq</TableHead>
                <TableHead className="w-16">Time</TableHead>
                <TableHead>Source</TableHead>
                <TableHead className="w-24">Kind</TableHead>
                <TableHead className="w-28">Hash</TableHead>
                <TableHead className="w-8"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {entries.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-slate-600 italic py-4">
                    No ledger entries yet…
                  </TableCell>
                </TableRow>
              )}
              {entries.map((entry) => (
                <Fragment key={entry.seq}>
                  <TableRow
                    className="cursor-pointer"
                    onClick={() => setExpanded(expanded === entry.seq ? null : entry.seq)}
                  >
                    <TableCell className="font-mono text-slate-400">{entry.seq}</TableCell>
                    <TableCell className="font-mono text-slate-500 text-xs">
                      {formatTime(entry.ts_iso)}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-slate-400 truncate max-w-32">
                      {entry.source}
                    </TableCell>
                    <TableCell>
                      <Badge variant={KIND_VARIANT[entry.kind] ?? "muted"} className="text-xs">
                        {entry.kind}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-slate-500">
                      {shortHash(entry.event_hash)}
                    </TableCell>
                    <TableCell className="text-slate-500">
                      {expanded === entry.seq ? "▲" : "▼"}
                    </TableCell>
                  </TableRow>
                  {expanded === entry.seq && (
                    <TableRow key={`${entry.seq}-detail`} className="bg-slate-900/50">
                      <TableCell colSpan={6} className="py-3">
                        <div className="space-y-2 text-xs font-mono">
                          <div>
                            <span className="text-slate-500">prev_hash: </span>
                            <span className="text-slate-400 break-all">{entry.prev_hash}</span>
                          </div>
                          <div>
                            <span className="text-slate-500">event_hash: </span>
                            <span className="text-slate-300 break-all">{entry.event_hash}</span>
                          </div>
                          <div>
                            <span className="text-slate-500">signature: </span>
                            <span className="text-blue-400 break-all">{entry.signature}</span>
                          </div>
                          <div>
                            <span className="text-slate-500">payload: </span>
                            <span className="text-green-400 break-all">{entry.payload_json}</span>
                          </div>
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </Fragment>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </Card>
  );
}
