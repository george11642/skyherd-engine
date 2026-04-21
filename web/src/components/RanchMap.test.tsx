import { describe, it, expect, vi, beforeEach } from "vitest";
import { render } from "@testing-library/react";
import { RanchMap } from "./RanchMap";

// Mock SSE client
vi.mock("@/lib/sse", () => ({
  getSSE: () => ({
    on: vi.fn(),
    off: vi.fn(),
  }),
}));

// Mock ResizeObserver
class MockResizeObserver {
  observe = vi.fn();
  disconnect = vi.fn();
  unobserve = vi.fn();
}
vi.stubGlobal("ResizeObserver", MockResizeObserver);

describe("RanchMap", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders a canvas element", () => {
    const { container } = render(<RanchMap />);
    const canvas = container.querySelector("canvas");
    expect(canvas).toBeTruthy();
  });

  it("canvas has correct data-testid", () => {
    const { getByTestId } = render(<RanchMap />);
    expect(getByTestId("ranch-map-canvas")).toBeTruthy();
  });

  it("canvas has accessible role and label", () => {
    const { getByRole } = render(<RanchMap />);
    const canvas = getByRole("img");
    expect(canvas).toBeTruthy();
    expect(canvas.getAttribute("aria-label")).toContain("Ranch map");
  });

  it("canvas has full size classes", () => {
    const { container } = render(<RanchMap />);
    const canvas = container.querySelector("canvas");
    expect(canvas?.className).toContain("w-full");
    expect(canvas?.className).toContain("h-full");
  });
});
