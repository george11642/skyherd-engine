import { describe, it, expect, vi } from "vitest";
import { render, fireEvent } from "@testing-library/react";
import { RightRailAccordion, type AccordionTab } from "./RightRailAccordion";

function makeTabs(): AccordionTab[] {
  return [
    { id: "a", label: "Alpha", render: () => <div data-testid="pane-a">Alpha content</div> },
    { id: "b", label: "Beta",  badge: 3, badgeVariant: "sage",
      render: () => <div data-testid="pane-b">Beta content</div> },
    { id: "c", label: "Gamma", render: () => <div data-testid="pane-c">Gamma content</div> },
  ];
}

describe("RightRailAccordion", () => {
  it("renders first tab as active by default", () => {
    const { queryByTestId } = render(<RightRailAccordion tabs={makeTabs()} />);
    expect(queryByTestId("pane-a")).toBeTruthy();
    expect(queryByTestId("pane-b")).toBeFalsy();
  });

  it("renders initialTabId when provided", () => {
    const { queryByTestId } = render(
      <RightRailAccordion tabs={makeTabs()} initialTabId="b" />,
    );
    expect(queryByTestId("pane-a")).toBeFalsy();
    expect(queryByTestId("pane-b")).toBeTruthy();
  });

  it("switches panels on tab click", () => {
    const { getByTestId, queryByTestId } = render(
      <RightRailAccordion tabs={makeTabs()} />,
    );
    fireEvent.click(getByTestId("rr-tab-c"));
    expect(queryByTestId("pane-a")).toBeFalsy();
    expect(queryByTestId("pane-c")).toBeTruthy();
  });

  it("renders badge for tab when badge is non-zero", () => {
    const { getByTestId } = render(<RightRailAccordion tabs={makeTabs()} />);
    const tabB = getByTestId("rr-tab-b");
    expect(tabB.textContent).toContain("3");
  });

  it("omits badge when badge is 0 or undefined", () => {
    const tabs: AccordionTab[] = [
      { id: "a", label: "A", badge: 0,     render: () => <span>a</span> },
      { id: "b", label: "B", badge: undefined, render: () => <span>b</span> },
    ];
    const { getByTestId } = render(<RightRailAccordion tabs={tabs} />);
    // label-only children — no additional chip
    expect(getByTestId("rr-tab-a").querySelectorAll(".chip").length).toBe(0);
    expect(getByTestId("rr-tab-b").querySelectorAll(".chip").length).toBe(0);
  });

  it("calls onTabChange when tab switches", () => {
    const onChange = vi.fn();
    const { getByTestId } = render(
      <RightRailAccordion tabs={makeTabs()} onTabChange={onChange} />,
    );
    fireEvent.click(getByTestId("rr-tab-b"));
    expect(onChange).toHaveBeenCalledWith("b");
  });

  it("cycles tabs with ArrowRight/ArrowDown", () => {
    const { getByTestId, queryByTestId } = render(
      <RightRailAccordion tabs={makeTabs()} />,
    );
    const tabA = getByTestId("rr-tab-a");
    fireEvent.keyDown(tabA, { key: "ArrowRight" });
    expect(queryByTestId("pane-b")).toBeTruthy();
    const tabB = getByTestId("rr-tab-b");
    fireEvent.keyDown(tabB, { key: "ArrowDown" });
    expect(queryByTestId("pane-c")).toBeTruthy();
  });

  it("wraps from last → first with ArrowRight", () => {
    const { getByTestId, queryByTestId } = render(
      <RightRailAccordion tabs={makeTabs()} initialTabId="c" />,
    );
    fireEvent.keyDown(getByTestId("rr-tab-c"), { key: "ArrowRight" });
    expect(queryByTestId("pane-a")).toBeTruthy();
  });

  it("Home jumps to first, End jumps to last", () => {
    const { getByTestId, queryByTestId } = render(
      <RightRailAccordion tabs={makeTabs()} initialTabId="b" />,
    );
    fireEvent.keyDown(getByTestId("rr-tab-b"), { key: "End" });
    expect(queryByTestId("pane-c")).toBeTruthy();
    fireEvent.keyDown(getByTestId("rr-tab-c"), { key: "Home" });
    expect(queryByTestId("pane-a")).toBeTruthy();
  });

  it("renders nothing if tabs is empty", () => {
    const { container } = render(<RightRailAccordion tabs={[]} />);
    expect(container.firstChild).toBeNull();
  });
});
