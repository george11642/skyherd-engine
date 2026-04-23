import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AgentLane } from "./AgentLane";

const AGENT_NAMES = [
  "FenceLineDispatcher",
  "HerdHealthWatcher",
  "PredatorPatternLearner",
  "GrazingOptimizer",
  "CalvingWatch",
];

describe("AgentLane", () => {
  it("renders the agent name", () => {
    render(
      <AgentLane
        agentName="FenceLineDispatcher"
        state="idle"
        events={[]}
      />,
    );
    expect(screen.getByText("FenceLineDispatcher")).toBeTruthy();
  });

  it("renders active badge when state is active", () => {
    render(
      <AgentLane agentName="HerdHealthWatcher" state="active" events={[]} />,
    );
    expect(screen.getByText("active")).toBeTruthy();
  });

  it("renders idle badge when state is idle", () => {
    render(
      <AgentLane agentName="GrazingOptimizer" state="idle" events={[]} />,
    );
    expect(screen.getByText("idle")).toBeTruthy();
  });

  it("has data-test='agent-lane' attribute", () => {
    const { container } = render(
      <AgentLane agentName="CalvingWatch" state="idle" events={[]} />,
    );
    const lane = container.querySelector("[data-test='agent-lane']");
    expect(lane).toBeTruthy();
  });

  it("has data-agent attribute matching agent name", () => {
    const { container } = render(
      <AgentLane agentName="PredatorPatternLearner" state="idle" events={[]} />,
    );
    const lane = container.querySelector("[data-agent='PredatorPatternLearner']");
    expect(lane).toBeTruthy();
  });

  it("renders log messages", () => {
    render(
      <AgentLane
        agentName="FenceLineDispatcher"
        state="active"
        events={[
          { ts: 1714000000, message: "Breach detected on seg_1", level: "INFO" },
          { ts: 1714000001, message: "Drone dispatched", level: "INFO" },
        ]}
      />,
    );
    expect(screen.getByText("Breach detected on seg_1")).toBeTruthy();
    expect(screen.getByText("Drone dispatched")).toBeTruthy();
  });

  it("shows waiting message when no events", () => {
    render(<AgentLane agentName="CalvingWatch" state="idle" events={[]} />);
    expect(screen.getByText(/waiting for events/i)).toBeTruthy();
  });

  it("renders skeleton loader rows when no events (B1)", () => {
    const { container, getByTestId } = render(
      <AgentLane agentName="CalvingWatch" state="idle" events={[]} />,
    );
    // The wrapper marker is present
    expect(getByTestId("agent-lane-skeleton")).toBeTruthy();
    // 3 skeleton rows inside
    const skeletons = container.querySelectorAll(
      "[data-testid='agent-lane-skeleton'] .skeleton",
    );
    expect(skeletons.length).toBe(3);
  });

  it("renders sparkline when eventRate has >= 2 values (B3)", () => {
    const { container } = render(
      <AgentLane
        agentName="HerdHealthWatcher"
        state="active"
        events={[{ ts: 1, message: "ok", level: "INFO" }]}
        eventRate={[0, 1, 2, 1, 0, 3, 2]}
      />,
    );
    const svg = container.querySelector("svg");
    expect(svg).toBeTruthy();
    expect(svg?.getAttribute("width")).toBe("48");
    expect(svg?.getAttribute("height")).toBe("16");
  });

  it("hides sparkline when eventRate is empty (B3)", () => {
    const { container } = render(
      <AgentLane
        agentName="HerdHealthWatcher"
        state="idle"
        events={[]}
        eventRate={[]}
      />,
    );
    expect(container.querySelector("svg")).toBeNull();
  });
});

describe("All 5 agent names render", () => {
  for (const name of AGENT_NAMES) {
    it(`renders ${name}`, () => {
      render(<AgentLane agentName={name} state="idle" events={[]} />);
      expect(screen.getByText(name)).toBeTruthy();
    });
  }
});
