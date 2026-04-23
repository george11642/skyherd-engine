/**
 * StatBand — animated-count test (Plan v1.1 Part B / B7).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { StatBand } from "./StatBand";

let sseHandlers: Record<string, ((payload: unknown) => void)[]> = {};

vi.mock("@/lib/sse", () => ({
  getSSE: () => ({
    on: (eventType: string, handler: (payload: unknown) => void) => {
      if (!sseHandlers[eventType]) sseHandlers[eventType] = [];
      sseHandlers[eventType].push(handler);
    },
    off: (eventType: string, handler: (payload: unknown) => void) => {
      sseHandlers[eventType] = (sseHandlers[eventType] ?? []).filter((h) => h !== handler);
    },
  }),
}));

function triggerSSE(eventType: string, payload: unknown) {
  (sseHandlers[eventType] ?? []).forEach((h) => h(payload));
}

describe("StatBand — animated chip counts (B2)", () => {
  beforeEach(() => {
    sseHandlers = {};
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ entries: [], ts: Date.now() / 1000 }),
      }),
    );
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("renders MESH / BUS / LEDGER / COST / UPTIME chips", async () => {
    await act(async () => {
      render(<StatBand />);
    });
    expect(screen.getByText(/MESH:/)).toBeTruthy();
    expect(screen.getByText(/BUS:/)).toBeTruthy();
    expect(screen.getByText(/LEDGER:/)).toBeTruthy();
    expect(screen.getByText(/COST:/)).toBeTruthy();
    expect(screen.getByText(/UPTIME:/)).toBeTruthy();
  });

  it("MESH count transitions from 0 to N across ticks", async () => {
    vi.useFakeTimers();
    await act(async () => {
      render(<StatBand />);
    });

    // Initial: 0 sessions (spring at rest, starts from value 0)
    expect(screen.getByText(/0 sessions/)).toBeTruthy();

    // Emit a cost tick with 3 active agents
    act(() => {
      triggerSSE("cost.tick", {
        agents: [
          { name: "a", state: "active" },
          { name: "b", state: "active" },
          { name: "c", state: "active" },
          { name: "d", state: "idle" },
          { name: "e", state: "idle" },
        ],
        all_idle: false,
        total_cumulative_usd: 0,
        rate_per_hr_usd: 0.24,
      });
    });

    // Advance timers so the spring settles
    await act(async () => {
      vi.advanceTimersByTime(1500);
    });

    // Spring should have settled at 3 sessions
    expect(screen.getByText(/3 sessions/)).toBeTruthy();
  });
});
