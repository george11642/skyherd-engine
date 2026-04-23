/**
 * HashChip — shared component.
 *
 * Renders a 4-swatch fingerprint derived from 4 x 6-hex-char groups of the
 * hash, followed by the short hash. Click copies the FULL hash via
 * navigator.clipboard.
 *
 * Accepts any hash string. If the hash is not pure hex (e.g. a base62
 * `memver_01XRSV...` ID), the swatches are derived from a sha256 digest of the
 * raw hash string — this keeps the visual shape identical regardless of input
 * format.
 *
 * Extracted from AttestationPanel.tsx (Phase 01 Plan 01) so MemoryPanel.tsx
 * (Plan 06) can reuse it.
 */

import { useState, useEffect } from "react";
import { Tooltip } from "@/components/ui/tooltip";

export interface HashChipProps {
  hash: string;
  label?: string;
}

const HEX_RE = /^[0-9a-fA-F]+$/;

function shortHash(h: string): string {
  if (!h || h.length < 12) return h ?? "—";
  return h.slice(0, 8) + "…" + h.slice(-4);
}

/**
 * Compute a sha256 hex digest of the given string using the Web Crypto API.
 * Returns null if crypto.subtle is unavailable (e.g. insecure context or
 * jsdom-without-crypto).
 */
async function sha256Hex(text: string): Promise<string | null> {
  try {
    if (typeof crypto === "undefined" || !crypto.subtle) return null;
    const buf = new TextEncoder().encode(text);
    const digest = await crypto.subtle.digest("SHA-256", buf);
    const bytes = new Uint8Array(digest);
    return Array.from(bytes)
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  } catch {
    return null;
  }
}

function fallbackHexFromString(text: string): string {
  // Deterministic non-crypto fallback: map each char to its two-digit hex code
  // mod 256, pad to 64 chars. Keeps swatches stable across renders for the
  // same input even without subtle crypto.
  let out = "";
  for (let i = 0; i < text.length && out.length < 64; i++) {
    out += (text.charCodeAt(i) % 256).toString(16).padStart(2, "0");
  }
  while (out.length < 64) out += "00";
  return out.slice(0, 64);
}

export function HashChip({ hash, label }: HashChipProps) {
  const [copied, setCopied] = useState(false);
  const [derivedHex, setDerivedHex] = useState<string | null>(null);

  const isPureHex = Boolean(hash) && hash.length >= 24 && HEX_RE.test(hash);

  useEffect(() => {
    if (!hash || isPureHex) {
      setDerivedHex(null);
      return;
    }
    let cancelled = false;
    sha256Hex(hash).then((digest) => {
      if (cancelled) return;
      setDerivedHex(digest ?? fallbackHexFromString(hash));
    });
    return () => {
      cancelled = true;
    };
  }, [hash, isPureHex]);

  if (!hash || hash.length < 12) {
    return <span>{hash ?? "—"}</span>;
  }

  const hexSource = isPureHex ? hash : (derivedHex ?? fallbackHexFromString(hash));

  const swatches: string[] = [];
  for (let i = 0; i < 4; i++) {
    const start = i * 6;
    const chunk = hexSource.slice(start, start + 6);
    if (chunk.length === 6) swatches.push(`#${chunk}`);
  }

  const handleCopy = async (e: React.MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(hash);
      setCopied(true);
      setTimeout(() => setCopied(false), 1000);
    } catch {
      // Clipboard API unavailable — silently ignore; tooltip still shows the hash.
    }
  };

  const tooltipContent = copied ? "copied!" : hash;
  const ariaLabel = label ? `Copy ${label} ${hash}` : `Copy hash ${hash}`;

  return (
    <Tooltip content={tooltipContent} className={copied ? "chip-sage" : undefined}>
      <button
        type="button"
        onClick={handleCopy}
        data-testid="hash-chip"
        className="inline-flex items-center gap-1.5 cursor-pointer"
        style={{
          background: "transparent",
          border: "none",
          padding: 0,
          fontFamily: "var(--font-mono)",
          fontSize: "0.6875rem",
          color: "var(--color-text-2)",
        }}
        aria-label={ariaLabel}
      >
        <span className="inline-flex shrink-0" aria-hidden="true">
          {swatches.map((c, i) => (
            <span
              key={i}
              data-testid="hash-swatch"
              style={{
                display: "inline-block",
                width: 8,
                height: 12,
                backgroundColor: c,
              }}
            />
          ))}
        </span>
        <span className="tabnum">{shortHash(hash)}</span>
      </button>
    </Tooltip>
  );
}
