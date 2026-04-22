import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import CrossRanchView from "./CrossRanchView";

// Mock SSE client
vi.mock("@/lib/sse", () => ({
  getSSE: () => ({
    on: vi.fn(),
    off: vi.fn(),
  }),
}));

// Mock framer-motion to avoid animation side-effects in tests
vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: React.ComponentPropsWithoutRef<"div">) => (
      <div {...props}>{children}</div>
    ),
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock ResizeObserver (used by RanchMap canvas)
class MockResizeObserver {
  observe = vi.fn();
  disconnect = vi.fn();
  unobserve = vi.fn();
}
vi.stubGlobal("ResizeObserver", MockResizeObserver);

describe("CrossRanchView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders without crashing", () => {
    const { container } = render(<CrossRanchView />);
    expect(container.firstChild).toBeTruthy();
  });

  it("shows Cross-Ranch heading text", () => {
    render(<CrossRanchView />);
    expect(screen.getByText("CROSS-RANCH MESH")).toBeTruthy();
  });

  it("shows SkyHerd brand in header", () => {
    const { container } = render(<CrossRanchView />);
    // "Sky" and "Herd" are in separate text nodes inside an <a> tag
    const link = container.querySelector("header a[href='/']");
    expect(link).toBeTruthy();
    expect(link!.textContent).toMatch(/sky.*herd/i);
  });

  it("shows Ranch A label", () => {
    render(<CrossRanchView />);
    expect(screen.getByText(/RANCH A/)).toBeTruthy();
  });

  it("shows Ranch B label", () => {
    render(<CrossRanchView />);
    expect(screen.getByText(/RANCH B/)).toBeTruthy();
  });

  it("shows handoff count chip", () => {
    render(<CrossRanchView />);
    expect(screen.getByText(/0 handoffs/i)).toBeTruthy();
  });

  it("renders two ranch map canvases", () => {
    const { container } = render(<CrossRanchView />);
    const canvases = container.querySelectorAll("canvas");
    expect(canvases.length).toBeGreaterThanOrEqual(2);
  });
});
