/**
 * RightRailAccordion — tabbed/accordion container for secondary panels.
 *
 * Phase 10 solves the "four panels fighting for vertical space" problem.
 * Shows one expanded section at a time, with a tab header for quick switch.
 * Keyboard: ArrowUp/ArrowDown cycle tabs, Enter activates.
 */

import { useState, useRef, type ReactNode, type KeyboardEvent } from "react";
import { cn } from "@/lib/cn";

export interface AccordionTab {
  id: string;
  label: string;
  /** Optional count badge shown on tab (e.g. 12 memory entries) */
  badge?: number | string;
  /** Tint for badge — matches chip variants */
  badgeVariant?: "sage" | "sky" | "dust" | "thermal" | "warn" | "danger" | "muted";
  render: () => ReactNode;
}

export interface RightRailAccordionProps {
  tabs: AccordionTab[];
  initialTabId?: string;
  /** Emitted when user switches tabs (for analytics / parent bookkeeping) */
  onTabChange?: (id: string) => void;
}

export function RightRailAccordion({
  tabs,
  initialTabId,
  onTabChange,
}: RightRailAccordionProps) {
  const [activeId, setActiveId] = useState<string>(initialTabId ?? tabs[0]?.id ?? "");
  const tabRefs = useRef<Record<string, HTMLButtonElement | null>>({});

  const active = tabs.find((t) => t.id === activeId) ?? tabs[0];

  const setActive = (id: string) => {
    setActiveId(id);
    onTabChange?.(id);
  };

  const handleKey = (e: KeyboardEvent<HTMLButtonElement>, idx: number) => {
    if (e.key === "ArrowRight" || e.key === "ArrowDown") {
      e.preventDefault();
      const nextIdx = (idx + 1) % tabs.length;
      const next = tabs[nextIdx];
      setActive(next.id);
      tabRefs.current[next.id]?.focus();
    } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
      e.preventDefault();
      const prevIdx = (idx - 1 + tabs.length) % tabs.length;
      const prev = tabs[prevIdx];
      setActive(prev.id);
      tabRefs.current[prev.id]?.focus();
    } else if (e.key === "Home") {
      e.preventDefault();
      setActive(tabs[0].id);
      tabRefs.current[tabs[0].id]?.focus();
    } else if (e.key === "End") {
      e.preventDefault();
      const last = tabs[tabs.length - 1];
      setActive(last.id);
      tabRefs.current[last.id]?.focus();
    }
  };

  if (!active) return null;

  return (
    <section
      className="flex flex-col overflow-hidden h-full rounded border"
      style={{
        backgroundColor: "var(--color-bg-1)",
        borderColor: "var(--color-line)",
      }}
      aria-label="Supporting panels"
    >
      <div
        role="tablist"
        aria-label="Panel selector"
        className="flex items-center gap-0 shrink-0 border-b overflow-x-auto"
        style={{ borderColor: "var(--color-line)" }}
      >
        {tabs.map((tab, idx) => {
          const isActive = tab.id === activeId;
          return (
            <button
              key={tab.id}
              ref={(el) => {
                tabRefs.current[tab.id] = el;
              }}
              role="tab"
              aria-selected={isActive}
              aria-controls={`rr-panel-${tab.id}`}
              id={`rr-tab-${tab.id}`}
              tabIndex={isActive ? 0 : -1}
              onClick={() => setActive(tab.id)}
              onKeyDown={(e) => handleKey(e, idx)}
              data-testid={`rr-tab-${tab.id}`}
              className={cn(
                "relative shrink-0 px-3 py-2 text-xs font-medium transition-colors cursor-pointer",
                isActive
                  ? "text-[var(--color-text-0)]"
                  : "text-[var(--color-text-2)] hover:text-[var(--color-text-1)]",
              )}
              style={{
                fontFamily: "var(--font-body)",
                letterSpacing: "0.01em",
              }}
            >
              <span className="inline-flex items-center gap-1.5">
                {tab.label}
                {tab.badge !== undefined && tab.badge !== null && tab.badge !== 0 && (
                  <span
                    className={cn(
                      "chip text-[10px]",
                      `chip-${tab.badgeVariant ?? "muted"}`,
                    )}
                    style={{ padding: "0 0.375rem", lineHeight: "14px" }}
                  >
                    {tab.badge}
                  </span>
                )}
              </span>
              {isActive && (
                <span
                  className="absolute bottom-0 left-0 right-0 h-0.5"
                  style={{ backgroundColor: "var(--color-accent-sage)" }}
                  aria-hidden="true"
                />
              )}
            </button>
          );
        })}
      </div>

      <div
        role="tabpanel"
        id={`rr-panel-${active.id}`}
        aria-labelledby={`rr-tab-${active.id}`}
        className="flex-1 min-h-0 overflow-hidden"
        data-testid={`rr-panel-${active.id}`}
      >
        {active.render()}
      </div>
    </section>
  );
}
