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
});

describe("All 5 agent names render", () => {
  for (const name of AGENT_NAMES) {
    it(`renders ${name}`, () => {
      render(<AgentLane agentName={name} state="idle" events={[]} />);
      expect(screen.getByText(name)).toBeTruthy();
    });
  }
});
