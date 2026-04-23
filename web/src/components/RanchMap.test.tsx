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

describe("RanchMap — predator pulse ring motion (DASH-05)", () => {
  it("predator ring stroke alpha varies across RAF ticks", async () => {
    // jsdom does not implement a real 2d context. Install a fake that records
    // every strokeStyle assignment; hand this fake back from getContext("2d").
    const strokeStyles: string[] = [];
    const makeFakeCtx = (): unknown => {
      let _ss: unknown = "#000";
      return {
        save: () => {},
        restore: () => {},
        scale: () => {},
        translate: () => {},
        fillRect: () => {},
        strokeRect: () => {},
        beginPath: () => {},
        closePath: () => {},
        moveTo: () => {},
        lineTo: () => {},
        arc: () => {},
        fill: () => {},
        stroke: () => {},
        fillText: () => {},
        setLineDash: () => {},
        createLinearGradient: () => ({ addColorStop: () => {} }),
        measureText: () => ({ width: 10 }),
        get strokeStyle() {
          return _ss;
        },
        set strokeStyle(v: unknown) {
          _ss = v;
          if (typeof v === "string" && v.includes("224,100,90")) {
            strokeStyles.push(v);
          }
        },
        fillStyle: "#000",
        lineWidth: 1,
        font: "",
        textAlign: "left",
      };
    };

    const origGetContext = HTMLCanvasElement.prototype.getContext;
    (HTMLCanvasElement.prototype as unknown as { getContext: unknown }).getContext =
      function (this: HTMLCanvasElement, kind: string) {
        if (kind === "2d") return makeFakeCtx();
        return null;
      };

    try {
      const snap = {
        cows: [],
        predators: [
          { id: "pr1", pos: [0.5, 0.5] as [number, number], species: "coyote" },
        ],
        drone: undefined,
      };
      const { rerender } = render(<RanchMap snapshot={snap} />);
      await new Promise((r) => setTimeout(r, 50));
      rerender(<RanchMap snapshot={snap} />);
      await new Promise((r) => setTimeout(r, 200));

      const alphas = strokeStyles
        .map((s) => {
          const m = s.match(/rgba\(\s*224\s*,\s*100\s*,\s*90\s*,\s*([\d.]+)\s*\)/);
          return m ? parseFloat(m[1]) : null;
        })
        .filter((a): a is number => a !== null);
      expect(alphas.length).toBeGreaterThanOrEqual(2);
      const first = alphas[0];
      expect(alphas.some((a) => Math.abs(a - first) > 0.01)).toBe(true);
    } finally {
      (HTMLCanvasElement.prototype as unknown as { getContext: unknown }).getContext =
        origGetContext;
    }
  });
});
