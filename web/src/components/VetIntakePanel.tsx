/**
 * VetIntakePanel — SCEN-01 + DASH-06 UI.
 *
 * Subscribes to the `vet_intake.drafted` SSE event (registered in
 * `@/lib/sse` eventTypes array by Plan 05-03). When an event arrives, the
 * panel records the intake in a list and lazily fetches the markdown body
 * from `/api/vet-intake/{id}`. Clicking a row opens the detail view, which
 * renders the markdown via a ~20-line inline renderer (no react-markdown —
 * per RESEARCH.md anti-patterns).
 *
 * DASH-06: the markdown body may contain a `## Structured Signals (DASH-06)`
 * section whose lines match
 *   `- kind=pixel_detection head=<name> bbox=[x0, y0, x1, y1] conf=<float>`
 * The panel parses these lines and renders a PixelDetectionChip for each
 * entry — surfacing Phase 2's VIS-05 bbox inside the rancher's vet-intake
 * packet without requiring a separate /api/ranch-map overlay.
 */

import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import { cn } from "@/lib/cn";
import { getSSE } from "@/lib/sse";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface VetIntakePayload {
  id: string;
  cow_tag: string;
  severity: string;
  disease?: string;
  path?: string;
  ts?: number;
}

export interface PixelDetection {
  head: string;
  bbox: [number, number, number, number];
  confidence: number;
}

interface IntakeRow extends VetIntakePayload {
  body?: string;
  loading?: boolean;
  error?: string;
}

type SeverityChip = "danger" | "warn" | "muted";

const SEVERITY_CHIP: Record<string, SeverityChip> = {
  escalate: "danger",
  observe: "warn",
  log: "muted",
};

const MAX_INTAKES = 20;

// ---------------------------------------------------------------------------
// Inline markdown renderer (~20 lines — converts ##, **bold**, bullets)
// ---------------------------------------------------------------------------

/**
 * Renders a restricted markdown subset to HTML.
 * Supported:
 *  - ## Heading            -> <h3>Heading</h3>
 *  - # Heading             -> <h2>Heading</h2>
 *  - **bold**              -> <strong>bold</strong>
 *  - `code`                -> <code>code</code>
 *  - - bullet              -> <li>bullet</li> inside <ul>
 *  - plain paragraphs.
 *
 * Every input is HTML-escaped before conversion so user content cannot
 * inject HTML. Output is safe to set via dangerouslySetInnerHTML.
 */
export function renderMarkdown(src: string): string {
  const esc = (s: string) =>
    s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  const lines = src.split(/\r?\n/);
  const out: string[] = [];
  let inList = false;
  for (const rawLine of lines) {
    const line = rawLine;
    if (/^##\s+/.test(line)) {
      if (inList) { out.push("</ul>"); inList = false; }
      out.push(`<h3>${inline(esc(line.replace(/^##\s+/, "")))}</h3>`);
    } else if (/^#\s+/.test(line)) {
      if (inList) { out.push("</ul>"); inList = false; }
      out.push(`<h2>${inline(esc(line.replace(/^#\s+/, "")))}</h2>`);
    } else if (/^-\s+/.test(line)) {
      if (!inList) { out.push("<ul>"); inList = true; }
      out.push(`<li>${inline(esc(line.replace(/^-\s+/, "")))}</li>`);
    } else if (line.trim() === "") {
      if (inList) { out.push("</ul>"); inList = false; }
      out.push("");
    } else {
      if (inList) { out.push("</ul>"); inList = false; }
      out.push(`<p>${inline(esc(line))}</p>`);
    }
  }
  if (inList) out.push("</ul>");
  return out.join("\n");
}

function inline(s: string): string {
  // **bold** — run before `code` so backticks inside bold survive
  let r = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  r = r.replace(/`([^`]+)`/g, "<code>$1</code>");
  return r;
}

// ---------------------------------------------------------------------------
// Pixel-detection parser (DASH-06)
// ---------------------------------------------------------------------------

const PIXEL_DETECTION_RE =
  /- kind=pixel_detection head=(\w+) bbox=\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\] conf=([\d.]+)/g;

export function parsePixelDetections(markdown: string): PixelDetection[] {
  const out: PixelDetection[] = [];
  if (!markdown) return out;
  const re = new RegExp(PIXEL_DETECTION_RE.source, "g");
  let m: RegExpExecArray | null;
  while ((m = re.exec(markdown)) !== null) {
    out.push({
      head: m[1],
      bbox: [Number(m[2]), Number(m[3]), Number(m[4]), Number(m[5])],
      confidence: Number(m[6]),
    });
  }
  return out;
}

// ---------------------------------------------------------------------------
// PixelDetectionChip (DASH-06)
// ---------------------------------------------------------------------------

interface PixelDetectionChipProps {
  detection: PixelDetection;
}

function PixelDetectionChip({ detection }: PixelDetectionChipProps) {
  const confPct = Math.round(detection.confidence * 100);
  const [x0, y0, x1, y1] = detection.bbox;
  return (
    <span
      data-testid="pixel-detection-chip"
      className="chip chip-thermal tabnum"
      title={`Phase 2 pixel head: ${detection.head} @ [${x0},${y0},${x1},${y1}] · ${detection.confidence.toFixed(2)}`}
      style={{ display: "inline-flex", gap: "0.35rem", alignItems: "center" }}
    >
      <strong>{detection.head}</strong>
      <span style={{ color: "var(--color-text-2)" }}>
        [{x0},{y0},{x1},{y1}]
      </span>
      <span>{confPct}%</span>
    </span>
  );
}

// ---------------------------------------------------------------------------
// VetIntakePanel
// ---------------------------------------------------------------------------

export interface VetIntakePanelProps {
  /** Optional fetch override — used by tests to inject deterministic markdown. */
  fetchIntake?: (id: string) => Promise<string>;
}

export function VetIntakePanel({ fetchIntake }: VetIntakePanelProps = {}) {
  const [intakes, setIntakes] = useState<IntakeRow[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const defaultFetch = useCallback(async (id: string): Promise<string> => {
    const resp = await fetch(`/api/vet-intake/${encodeURIComponent(id)}`);
    if (!resp.ok) {
      throw new Error(`fetch /api/vet-intake/${id} failed: ${resp.status}`);
    }
    return resp.text();
  }, []);
  const fetcher = fetchIntake ?? defaultFetch;

  const handleDrafted = useCallback(
    (payload: unknown) => {
      const p = payload as VetIntakePayload;
      if (!p || typeof p.id !== "string") return;
      setIntakes((prev) => {
        if (prev.some((row) => row.id === p.id)) return prev;
        const next = [{ ...p, loading: true }, ...prev].slice(0, MAX_INTAKES);
        return next;
      });
      // Fire the fetch — resolve into the row when done.
      fetcher(p.id)
        .then((body) => {
          setIntakes((prev) =>
            prev.map((row) =>
              row.id === p.id ? { ...row, body, loading: false } : row,
            ),
          );
        })
        .catch((err: unknown) => {
          const msg = err instanceof Error ? err.message : String(err);
          setIntakes((prev) =>
            prev.map((row) =>
              row.id === p.id
                ? { ...row, error: msg, loading: false }
                : row,
            ),
          );
        });
    },
    [fetcher],
  );

  useEffect(() => {
    const sse = getSSE();
    sse.on("vet_intake.drafted", handleDrafted);
    return () => sse.off("vet_intake.drafted", handleDrafted);
  }, [handleDrafted]);

  return (
    <section
      className="shrink-0 rounded border flex flex-col overflow-hidden"
      style={{
        maxHeight: "320px",
        backgroundColor: "var(--color-bg-1)",
        borderColor: "var(--color-line)",
      }}
      aria-label="Vet intake packets"
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-3 py-2 shrink-0 border-b"
        style={{ borderColor: "var(--color-line)" }}
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
          Vet Intake
        </span>
        <span className="chip chip-muted tabnum">{intakes.length} packet{intakes.length === 1 ? "" : "s"}</span>
      </div>

      {/* List */}
      <div className="flex-1 overflow-auto" style={{ fontFamily: "var(--font-mono)", fontSize: "0.6875rem" }}>
        {intakes.length === 0 && (
          <div
            data-testid="vet-intake-skeleton"
            className="px-3 py-3 flex flex-col"
            style={{ gap: "6px" }}
            aria-label="waiting for vet intakes"
          >
            <div className="skeleton" style={{ height: 10, width: "60%" }} />
            <span className="chip chip-muted" style={{ alignSelf: "flex-start" }}>
              watching HerdHealthWatcher · live
            </span>
            <span className="sr-only">no vet intakes yet</span>
          </div>
        )}
        {intakes.map((row) => {
          const variant = SEVERITY_CHIP[row.severity] ?? "muted";
          const isExpanded = expandedId === row.id;
          return (
            <Fragment key={row.id}>
              <div
                role="button"
                tabIndex={0}
                onClick={() => setExpandedId(isExpanded ? null : row.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setExpandedId(isExpanded ? null : row.id);
                  }
                }}
                className={cn(
                  "flex items-center gap-2 px-3 py-1 cursor-pointer transition-colors",
                  isExpanded ? "bg-[var(--color-bg-2)]" : "hover:bg-[var(--color-bg-2)/50]",
                )}
                style={{ borderBottom: `1px solid var(--color-line)` }}
                aria-expanded={isExpanded}
              >
                <span
                  data-testid={`severity-chip-${row.id}`}
                  className={`chip chip-${variant} tabnum`}
                >
                  {row.severity.toUpperCase()}
                </span>
                <span style={{ color: "var(--color-text-0)" }}>{row.cow_tag}</span>
                {row.disease && (
                  <span style={{ color: "var(--color-text-2)" }}>· {row.disease}</span>
                )}
                {row.loading && (
                  <span className="chip chip-muted tabnum">loading…</span>
                )}
                {row.error && (
                  <span className="chip chip-warn tabnum" title={row.error}>error</span>
                )}
              </div>
              {isExpanded && (
                <IntakeDetail row={row} />
              )}
            </Fragment>
          );
        })}
      </div>
    </section>
  );
}

interface IntakeDetailProps {
  row: IntakeRow;
}

function IntakeDetail({ row }: IntakeDetailProps) {
  const detections = useMemo(
    () => (row.body ? parsePixelDetections(row.body) : []),
    [row.body],
  );
  const html = useMemo(
    () => (row.body ? renderMarkdown(row.body) : ""),
    [row.body],
  );
  return (
    <div
      className="px-3 py-2"
      style={{
        backgroundColor: "var(--color-bg-2)",
        borderBottom: `1px solid var(--color-line)`,
      }}
    >
      {detections.length > 0 && (
        <div
          className="flex flex-wrap gap-1 mb-2"
          aria-label="Pixel detections"
        >
          {detections.map((d, i) => (
            <PixelDetectionChip key={`${d.head}-${i}`} detection={d} />
          ))}
        </div>
      )}
      {row.body ? (
        <div
          className="prose prose-sm"
          style={{ color: "var(--color-text-1)", fontFamily: "var(--font-sans)" }}
          dangerouslySetInnerHTML={{ __html: html }}
        />
      ) : row.error ? (
        <div style={{ color: "var(--color-accent-warn)" }}>Error: {row.error}</div>
      ) : (
        <div style={{ color: "var(--color-text-2)" }}>Loading…</div>
      )}
    </div>
  );
}

export default VetIntakePanel;
