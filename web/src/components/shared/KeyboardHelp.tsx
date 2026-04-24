/**
 * KeyboardHelp — press `?` anywhere to open shortcut overlay.
 *
 * Documents every dashboard-wide shortcut so judges and ranchers know
 * they can drive the UI without the mouse. Lightweight (no modal lib),
 * trap-focuses on first kbd, Esc closes.
 */

import { useState, useEffect, useRef } from "react";
import { cn } from "@/lib/cn";

interface Shortcut {
  keys: string[];
  description: string;
  category: string;
}

const SHORTCUTS: Shortcut[] = [
  { keys: ["?"],           description: "Open / close this help overlay",        category: "Help" },
  { keys: ["Esc"],         description: "Close overlay",                          category: "Help" },
  { keys: ["→", "↓"],      description: "Next panel tab (Right Rail)",            category: "Navigation" },
  { keys: ["←", "↑"],      description: "Previous panel tab (Right Rail)",        category: "Navigation" },
  { keys: ["Home"],        description: "Jump to first panel tab",                category: "Navigation" },
  { keys: ["End"],         description: "Jump to last panel tab",                 category: "Navigation" },
  { keys: ["Tab"],         description: "Move focus to next interactive element", category: "Navigation" },
];

export function KeyboardHelp() {
  const [open, setOpen] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const inInput =
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable);
      if (e.key === "?" && !inInput) {
        e.preventDefault();
        setOpen((v) => !v);
      } else if (e.key === "Escape" && open) {
        setOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  useEffect(() => {
    if (open) dialogRef.current?.focus();
  }, [open]);

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        aria-label="Open keyboard shortcut help"
        title="Keyboard shortcuts (press ?)"
        data-testid="keyboard-help-open"
        className={cn(
          "fixed bottom-3 right-3 z-40 w-8 h-8 rounded-full",
          "flex items-center justify-center cursor-pointer transition-colors",
          "border text-sm font-mono",
        )}
        style={{
          backgroundColor: "var(--color-bg-1)",
          borderColor: "var(--color-line)",
          color: "var(--color-text-2)",
        }}
      >
        ?
      </button>
    );
  }

  const categories = Array.from(new Set(SHORTCUTS.map((s) => s.category)));

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="kbd-help-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backgroundColor: "rgba(10,12,16,0.72)" }}
      onClick={() => setOpen(false)}
      data-testid="keyboard-help-dialog"
    >
      <div
        ref={dialogRef}
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md rounded border p-5"
        style={{
          backgroundColor: "var(--color-bg-1)",
          borderColor: "var(--color-line)",
        }}
      >
        <div className="flex items-center justify-between mb-4">
          <h2
            id="kbd-help-title"
            className="font-semibold"
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "1rem",
              letterSpacing: "-0.01em",
              color: "var(--color-text-0)",
            }}
          >
            Keyboard shortcuts
          </h2>
          <button
            onClick={() => setOpen(false)}
            aria-label="Close shortcut help"
            data-testid="keyboard-help-close"
            className="text-xs cursor-pointer"
            style={{ color: "var(--color-text-2)" }}
          >
            Esc
          </button>
        </div>

        <div className="flex flex-col gap-4">
          {categories.map((cat) => (
            <div key={cat}>
              <div
                className="text-[10px] uppercase tracking-wider mb-2"
                style={{ color: "var(--color-text-2)", letterSpacing: "0.08em" }}
              >
                {cat}
              </div>
              <dl className="flex flex-col gap-1.5">
                {SHORTCUTS.filter((s) => s.category === cat).map((s, idx) => (
                  <div
                    key={`${cat}-${idx}`}
                    className="flex items-center justify-between gap-3"
                  >
                    <dt
                      className="text-xs"
                      style={{ color: "var(--color-text-1)" }}
                    >
                      {s.description}
                    </dt>
                    <dd className="flex items-center gap-1 shrink-0">
                      {s.keys.map((k) => (
                        <kbd
                          key={k}
                          className="inline-flex items-center justify-center px-1.5 rounded"
                          style={{
                            minWidth: "22px",
                            height: "22px",
                            backgroundColor: "var(--color-bg-2)",
                            borderColor: "var(--color-line)",
                            border: "1px solid",
                            color: "var(--color-text-0)",
                            fontFamily: "var(--font-mono)",
                            fontSize: "11px",
                          }}
                        >
                          {k}
                        </kbd>
                      ))}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          ))}
        </div>

        <div
          className="mt-4 pt-3 text-[11px] border-t"
          style={{
            borderColor: "var(--color-line)",
            color: "var(--color-text-2)",
            fontFamily: "var(--font-mono)",
          }}
        >
          Press <kbd>?</kbd> anywhere to toggle. Tap outside to dismiss.
        </div>
      </div>
    </div>
  );
}
