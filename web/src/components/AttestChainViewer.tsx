/**
 * AttestChainViewer — public /attest/:hash viewer page.
 *
 * Shows the chain back to genesis for a given event hash with per-entry
 * signature verification status. Fetches:
 *   GET /api/attest/by-hash/{hash}   — list of entries seq 1..N
 *   POST /api/attest/verify          — bulk chain verify (used to compute
 *                                       per-row PASS/FAIL from first_bad_seq)
 *
 * ATT-01 (Phase 4).
 */

import { useEffect, useState } from "react";
import { HashChip } from "@/components/shared/HashChip";

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
  memver_id?: string | null;
}

interface ChainResponse {
  target: string;
  chain: LedgerEntry[];
  ts: number;
}

interface VerifyResult {
  valid: boolean;
  total: number;
  first_bad_seq?: number | null;
  reason?: string | null;
}

export interface AttestChainViewerProps {
  hash: string;
}

type LoadState = "loading" | "ready" | "not_found" | "error";

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString("en-US", { hour12: false });
  } catch {
    return iso;
  }
}

function rowStatus(
  seq: number,
  verify: VerifyResult | null,
): "pending" | "valid" | "invalid" {
  if (!verify) return "pending";
  if (verify.valid) return "valid";
  if (verify.first_bad_seq == null) return "invalid";
  if (seq < verify.first_bad_seq) return "valid";
  if (seq === verify.first_bad_seq) return "invalid";
  return "pending";
}

export function AttestChainViewer({ hash }: AttestChainViewerProps) {
  const [state, setState] = useState<LoadState>("loading");
  const [chain, setChain] = useState<LedgerEntry[]>([]);
  const [verify, setVerify] = useState<VerifyResult | null>(null);

  useEffect(() => {
    let aborted = false;

    async function load(): Promise<void> {
      try {
        const resp = await fetch(
          `/api/attest/by-hash/${encodeURIComponent(hash)}`,
        );
        if (resp.status === 404) {
          if (!aborted) setState("not_found");
          return;
        }
        if (!resp.ok) {
          if (!aborted) setState("error");
          return;
        }
        const data = (await resp.json()) as ChainResponse;
        if (aborted) return;
        setChain(data.chain ?? []);
        setState("ready");

        // Kick off verify in parallel.
        const verifyResp = await fetch("/api/attest/verify", { method: "POST" });
        if (!aborted && verifyResp.ok) {
          const v = (await verifyResp.json()) as VerifyResult;
          setVerify(v);
        }
      } catch {
        if (!aborted) setState("error");
      }
    }

    void load();
    return () => {
      aborted = true;
    };
  }, [hash]);

  return (
    <div
      className="min-h-full p-6"
      style={{ backgroundColor: "var(--color-bg-0)", color: "var(--color-text-0)" }}
    >
      <header className="mb-4">
        <h1
          className="font-semibold"
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "1.125rem",
            letterSpacing: "-0.01em",
          }}
        >
          Attestation Chain
        </h1>
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.75rem",
            color: "var(--color-text-2)",
          }}
          data-testid="viewer-target-hash"
        >
          target: <span style={{ color: "var(--color-text-0)" }}>{hash}</span>
        </div>
      </header>

      {state === "loading" && (
        <p data-testid="viewer-loading" style={{ color: "var(--color-text-2)" }}>
          Loading chain…
        </p>
      )}

      {state === "not_found" && (
        <p
          data-testid="viewer-not-found"
          className="chip chip-warn"
        >
          No ledger entry with this hash.
        </p>
      )}

      {state === "error" && (
        <p data-testid="viewer-error" className="chip chip-danger">
          Failed to load chain.
        </p>
      )}

      {state === "ready" && (
        <section aria-label="Attestation chain" data-testid="viewer-chain">
          <div
            className="mb-3 flex items-center gap-2"
            style={{ fontSize: "0.75rem" }}
          >
            <span className="chip chip-muted tabnum">
              {chain.length} entries
            </span>
            {verify === null && (
              <span className="chip chip-sky">Verifying…</span>
            )}
            {verify?.valid && (
              <span className="chip chip-sage tabnum">CHAIN VALID</span>
            )}
            {verify && !verify.valid && (
              <span className="chip chip-danger tabnum">
                INVALID @ seq={verify.first_bad_seq ?? "?"}
              </span>
            )}
          </div>

          <table className="w-full text-left border-collapse text-mono-xs">
            <thead>
              <tr style={{ borderBottom: "1px solid var(--color-line)" }}>
                {["SEQ", "TIME", "SOURCE", "KIND", "HASH", "VERIFY"].map((h) => (
                  <th
                    key={h}
                    className="px-3 py-1 font-medium tabnum"
                    style={{
                      color: "var(--color-text-2)",
                      fontSize: "0.5625rem",
                      letterSpacing: "0.06em",
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {chain.map((entry) => {
                const status = rowStatus(entry.seq, verify);
                return (
                  <tr
                    key={entry.seq}
                    style={{ borderBottom: "1px solid var(--color-line)" }}
                    data-testid={`viewer-row-${entry.seq}`}
                  >
                    <td className="px-3 py-1 tabnum">{entry.seq}</td>
                    <td
                      className="px-3 py-1 tabnum whitespace-nowrap"
                      style={{ color: "var(--color-text-2)" }}
                    >
                      {formatTime(entry.ts_iso)}
                    </td>
                    <td className="px-3 py-1" title={entry.source}>
                      {entry.source}
                    </td>
                    <td className="px-3 py-1">
                      <span className="chip chip-muted">{entry.kind}</span>
                    </td>
                    <td className="px-3 py-1">
                      <HashChip hash={entry.event_hash} />
                    </td>
                    <td className="px-3 py-1">
                      {status === "pending" && (
                        <span
                          className="chip chip-muted tabnum"
                          data-testid={`verify-status-${entry.seq}`}
                        >
                          …
                        </span>
                      )}
                      {status === "valid" && (
                        <span
                          className="chip chip-sage tabnum"
                          data-testid={`verify-status-${entry.seq}`}
                        >
                          ✓ Verified
                        </span>
                      )}
                      {status === "invalid" && (
                        <span
                          className="chip chip-danger tabnum"
                          data-testid={`verify-status-${entry.seq}`}
                        >
                          ✗ Invalid
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
