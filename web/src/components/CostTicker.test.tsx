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
  getReplayIfActive: () => null,
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

describe("CostTicker — paused state visual treatment (DASH-03)", () => {
  beforeEach(() => {
    sseHandlers = {};
  });

  it("dims the cumulative cost with opacity<0.5 or grayscale when all_idle=true", () => {
    render(
      <CostTicker
        all_idle={true}
        total_cumulative_usd={0.123456}
        rate_per_hr_usd={0.0}
        agents={[]}
        sparkline={[0.01, 0.02, 0.03, 0.04]}
      />,
    );
    const dollar = screen.getByText(/\$0\.12/);
    let el: HTMLElement | null = dollar;
    let foundDim = false;
    while (el && el.parentElement) {
      const op = parseFloat((el.style.opacity as string) || "1");
      const filter = el.style.filter || "";
      if (op < 0.5 || filter.includes("grayscale")) {
        foundDim = true;
        break;
      }
      el = el.parentElement;
    }
    expect(foundDim).toBe(true);
  });

  it("leaves the cumulative cost at full opacity when all_idle=false", () => {
    render(
      <CostTicker
        all_idle={false}
        total_cumulative_usd={0.123456}
        rate_per_hr_usd={0.08}
        agents={[]}
        sparkline={[0.01, 0.02, 0.03, 0.04]}
      />,
    );
    const dollar = screen.getByText(/\$0\.12/);
    let el: HTMLElement | null = dollar;
    let dimmed = false;
    while (el && el.parentElement) {
      const op = parseFloat((el.style.opacity as string) || "1");
      const filter = el.style.filter || "";
      if (op < 0.9 || filter.includes("grayscale(1)")) {
        dimmed = true;
        break;
      }
      el = el.parentElement;
    }
    expect(dimmed).toBe(false);
  });

  it("freezes the sparkline to a flat line when all_idle=true", () => {
    const { container } = render(
      <CostTicker
        all_idle={true}
        total_cumulative_usd={0.1}
        rate_per_hr_usd={0.0}
        agents={[]}
        sparkline={[0.01, 0.02, 0.03, 0.04, 0.05]}
      />,
    );
    const poly = container.querySelector("polyline, path[d]");
    if (poly) {
      const pts = poly.getAttribute("points") || poly.getAttribute("d") || "";
      const ys = Array.from(pts.matchAll(/[,\s](\d+(?:\.\d+)?)/g)).map((m) => m[1]);
      const uniqueY = new Set(ys);
      expect(uniqueY.size).toBeLessThanOrEqual(2);
    }
  });
});
