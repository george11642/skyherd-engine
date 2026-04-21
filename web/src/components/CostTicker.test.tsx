import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { CostTicker } from "./CostTicker";

// We need to be able to trigger SSE events in tests
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

describe("CostTicker", () => {
  beforeEach(() => {
    sseHandlers = {};
  });

  it("renders without crashing", () => {
    render(<CostTicker />);
  });

  it("shows PAUSED idle state initially", () => {
    render(<CostTicker />);
    expect(screen.getByText(/paused.*idle/i)).toBeTruthy();
  });

  it("shows $0.08/hr when active agents present", () => {
    render(<CostTicker />);
    act(() => {
      triggerSSE("cost.tick", {
        ts: Date.now() / 1000,
        seq: 1,
        agents: [
          { name: "FenceLineDispatcher", state: "active", cost_delta_usd: 0.0, cumulative_cost_usd: 0.001, tokens_in: 100, tokens_out: 40 },
          { name: "HerdHealthWatcher", state: "idle", cost_delta_usd: 0.0, cumulative_cost_usd: 0.0, tokens_in: 0, tokens_out: 0 },
          { name: "PredatorPatternLearner", state: "idle", cost_delta_usd: 0.0, cumulative_cost_usd: 0.0, tokens_in: 0, tokens_out: 0 },
          { name: "GrazingOptimizer", state: "idle", cost_delta_usd: 0.0, cumulative_cost_usd: 0.0, tokens_in: 0, tokens_out: 0 },
          { name: "CalvingWatch", state: "idle", cost_delta_usd: 0.0, cumulative_cost_usd: 0.0, tokens_in: 0, tokens_out: 0 },
        ],
        all_idle: false,
        rate_per_hr_usd: 0.08,
        total_cumulative_usd: 0.001,
      });
    });
    // The literal string "$0.08/hr" must appear in the DOM (multiple elements ok)
    const matches = screen.getAllByText(/\$0\.08\/hr/);
    expect(matches.length).toBeGreaterThan(0);
  });

  it("shows idle/paused when all agents idle", () => {
    render(<CostTicker />);
    act(() => {
      triggerSSE("cost.tick", {
        ts: Date.now() / 1000,
        seq: 2,
        agents: [
          { name: "FenceLineDispatcher", state: "idle", cost_delta_usd: 0.0, cumulative_cost_usd: 0.0, tokens_in: 0, tokens_out: 0 },
          { name: "HerdHealthWatcher", state: "idle", cost_delta_usd: 0.0, cumulative_cost_usd: 0.0, tokens_in: 0, tokens_out: 0 },
          { name: "PredatorPatternLearner", state: "idle", cost_delta_usd: 0.0, cumulative_cost_usd: 0.0, tokens_in: 0, tokens_out: 0 },
          { name: "GrazingOptimizer", state: "idle", cost_delta_usd: 0.0, cumulative_cost_usd: 0.0, tokens_in: 0, tokens_out: 0 },
          { name: "CalvingWatch", state: "idle", cost_delta_usd: 0.0, cumulative_cost_usd: 0.0, tokens_in: 0, tokens_out: 0 },
        ],
        all_idle: true,
        rate_per_hr_usd: 0.0,
        total_cumulative_usd: 0.0,
      });
    });
    // Must show paused/idle indicator (multiple matches acceptable)
    const pausedMatches = screen.getAllByText(/paused/i);
    expect(pausedMatches.length).toBeGreaterThan(0);
    // Must mention idle somewhere
    const html = document.body.innerHTML;
    expect(html).toContain("idle");
  });

  it("contains literal '$0.08/hr' string in DOM when active", () => {
    render(<CostTicker />);
    act(() => {
      triggerSSE("cost.tick", {
        ts: Date.now() / 1000,
        seq: 3,
        agents: [
          { name: "FenceLineDispatcher", state: "active", cost_delta_usd: 0.00002, cumulative_cost_usd: 0.005, tokens_in: 200, tokens_out: 80 },
          { name: "HerdHealthWatcher", state: "active", cost_delta_usd: 0.00002, cumulative_cost_usd: 0.003, tokens_in: 150, tokens_out: 60 },
          { name: "PredatorPatternLearner", state: "idle", cost_delta_usd: 0.0, cumulative_cost_usd: 0.0, tokens_in: 0, tokens_out: 0 },
          { name: "GrazingOptimizer", state: "idle", cost_delta_usd: 0.0, cumulative_cost_usd: 0.0, tokens_in: 0, tokens_out: 0 },
          { name: "CalvingWatch", state: "idle", cost_delta_usd: 0.0, cumulative_cost_usd: 0.0, tokens_in: 0, tokens_out: 0 },
        ],
        all_idle: false,
        rate_per_hr_usd: 0.08,
        total_cumulative_usd: 0.008,
      });
    });
    const html = document.body.innerHTML;
    expect(html).toContain("$0.08/hr");
  });

  it("renders cost meter label", () => {
    render(<CostTicker />);
    expect(screen.getByText(/cost meter/i)).toBeTruthy();
  });
});
