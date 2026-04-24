/**
 * ScenarioStrip — scenario.active SSE event applies .scenario-active class.
 * Plan v1.1 Part B / B7.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, act } from "@testing-library/react";
import { ScenarioStrip } from "./ScenarioStrip";

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

describe("ScenarioStrip", () => {
  beforeEach(() => {
    sseHandlers = {};
  });

  it("renders all scenario pills", () => {
    const { container } = render(<ScenarioStrip />);
    const buttons = container.querySelectorAll("button");
    expect(buttons.length).toBeGreaterThanOrEqual(8);
  });

  it("active pill carries .scenario-active class on scenario.active SSE (B4)", () => {
    const { container } = render(<ScenarioStrip />);
    act(() => {
      triggerSSE("scenario.active", {
        name: "coyote",
        pass_idx: 0,
        speed: 1,
        started_at: "2026-04-22T10:00:00Z",
      });
    });
    const active = container.querySelector(".scenario-active");
    expect(active).toBeTruthy();
    expect(active?.textContent).toContain("COYOTE");
  });

  it("scenario.ended clears active state (B4)", () => {
    const { container } = render(<ScenarioStrip />);
    act(() => {
      triggerSSE("scenario.active", { name: "coyote", started_at: "2026-04-22T10:00:00Z" });
    });
    expect(container.querySelector(".scenario-active")).toBeTruthy();
    act(() => {
      triggerSSE("scenario.ended", { name: "coyote", outcome: "passed" });
    });
    expect(container.querySelector(".scenario-active")).toBeNull();
  });
});
