import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, act } from "@testing-library/react";
import { RanchMap, ScenarioBreadcrumb, classifyCow, applySnapshotToTweens } from "./RanchMap";
import { tweenValue } from "@/lib/tween";

// Mock SSE client — shared across both RanchMap and ScenarioBreadcrumb suites.
// A mutable handler map lets the breadcrumb tests re-emit scenario.active /
// scenario.ended to drive state transitions.
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
    sseHandlers = {};
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

describe("ScenarioBreadcrumb (B4)", () => {
  beforeEach(() => {
    sseHandlers = {};
  });

  it("renders nothing when no scenario is active", () => {
    const { queryByTestId } = render(<ScenarioBreadcrumb />);
    expect(queryByTestId("scenario-breadcrumb")).toBeNull();
  });

  it("renders SCENARIO chip after scenario.active SSE", () => {
    const { queryByTestId } = render(<ScenarioBreadcrumb />);
    act(() => {
      triggerSSE("scenario.active", {
        name: "coyote",
        pass_idx: 0,
        speed: 1,
        started_at: new Date().toISOString(),
      });
    });
    const chip = queryByTestId("scenario-breadcrumb");
    expect(chip).toBeTruthy();
    expect(chip?.textContent).toContain("SCENARIO");
    expect(chip?.textContent).toContain("COYOTE");
  });

  it("hides again after scenario.ended SSE", () => {
    const { queryByTestId } = render(<ScenarioBreadcrumb />);
    act(() => {
      triggerSSE("scenario.active", {
        name: "sick_cow",
        started_at: new Date().toISOString(),
      });
    });
    expect(queryByTestId("scenario-breadcrumb")).toBeTruthy();
    act(() => {
      triggerSSE("scenario.ended", { name: "sick_cow", outcome: "passed" });
    });
    expect(queryByTestId("scenario-breadcrumb")).toBeNull();
  });
});

describe("classifyCow (Phase 10)", () => {
  it("returns 'healthy' for normal bcs + grazing state", () => {
    expect(classifyCow({ id: "c1", pos: [0.5, 0.5], bcs: 5.5, state: "grazing" })).toBe("healthy");
  });

  it("returns 'sick' when state is sick", () => {
    expect(classifyCow({ id: "c1", pos: [0.5, 0.5], bcs: 5, state: "sick" })).toBe("sick");
  });

  it("returns 'calving' when state is calving", () => {
    expect(classifyCow({ id: "c1", pos: [0.5, 0.5], bcs: 5, state: "calving" })).toBe("calving");
  });

  it("returns 'calving' when state is labor", () => {
    expect(classifyCow({ id: "c1", pos: [0.5, 0.5], bcs: 5, state: "labor" })).toBe("calving");
  });

  it("returns 'sick' for severely thin cow (bcs < 3)", () => {
    expect(classifyCow({ id: "c1", pos: [0.5, 0.5], bcs: 2.5 })).toBe("sick");
  });

  it("returns 'watch' for moderately thin cow (bcs < 4)", () => {
    expect(classifyCow({ id: "c1", pos: [0.5, 0.5], bcs: 3.5 })).toBe("watch");
  });

  it("returns 'watch' when state is resting", () => {
    expect(classifyCow({ id: "c1", pos: [0.5, 0.5], bcs: 6, state: "resting" })).toBe("watch");
  });

  it("defaults to 'healthy' when bcs is missing", () => {
    expect(classifyCow({ id: "c1", pos: [0.5, 0.5] })).toBe("healthy");
  });

  it("sick state overrides otherwise-healthy bcs", () => {
    expect(classifyCow({ id: "c1", pos: [0.5, 0.5], bcs: 6, state: "sick" })).toBe("sick");
  });
});

describe("RanchMap — scenario zone glow (Phase 10)", () => {
  beforeEach(() => {
    sseHandlers = {};
  });

  it("subscribes to scenario.active / scenario.ended", () => {
    render(<RanchMap />);
    expect(sseHandlers["scenario.active"]?.length ?? 0).toBeGreaterThan(0);
    expect(sseHandlers["scenario.ended"]?.length ?? 0).toBeGreaterThan(0);
  });

  it("ignores scenario.active with no name", () => {
    render(<RanchMap />);
    // These must not throw — the internal scenarioToZone handles undefined safely
    act(() => { triggerSSE("scenario.active", {}); });
    act(() => { triggerSSE("scenario.ended", {}); });
    act(() => { triggerSSE("scenario.active", { name: "coyote" }); });
    act(() => { triggerSSE("scenario.active", { name: "water_drop" }); });
    act(() => { triggerSSE("scenario.active", { name: "sick_cow" }); });
    act(() => { triggerSSE("scenario.active", { name: "calving" }); });
    act(() => { triggerSSE("scenario.active", { name: "storm" }); });
    act(() => { triggerSSE("scenario.active", { name: "unknown" }); });
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

// ---------------------------------------------------------------------------
// Shared RAF tween pipeline (Phase 10.5 — DASH10-09 + scope expansion)
// ---------------------------------------------------------------------------

// Helper: build an empty state object typed to the `applySnapshotToTweens`
// signature. Avoids exporting the `EntityState` interface from production code
// purely for test wiring.
type EntityStateArg = Parameters<typeof applySnapshotToTweens>[0];
function makeState(): EntityStateArg {
  return {
    cows: new Map(),
    predators: new Map(),
    drone: null,
    trail: [],
    lastDroneTarget: null,
    seenCowIds: new Set<string>(),
    seenPredatorIds: new Set<string>(),
  } as EntityStateArg;
}

describe("applySnapshotToTweens — cows", () => {
  it("seeds a new cow at its target position with no motion", () => {
    const state = makeState();
    const snap = {
      cows: [{ id: "c1", pos: [0.3, 0.4] as [number, number], bcs: 5 }],
      predators: [],
    };
    applySnapshotToTweens(state, snap, 1000, false);
    const rec = state.cows.get("c1");
    expect(rec).toBeDefined();
    if (!rec) return;
    expect(tweenValue(rec.xTween, 1000)).toBeCloseTo(0.3, 5);
    expect(tweenValue(rec.yTween, 1000)).toBeCloseTo(0.4, 5);
    // After the full duration — still at target
    expect(tweenValue(rec.xTween, 2000)).toBeCloseTo(0.3, 5);
  });

  it("tweens cow position toward new target over 800ms (ease-out-cubic)", () => {
    const state = makeState();
    // Snapshot 1: cow at (0.2, 0.2)
    applySnapshotToTweens(
      state,
      { cows: [{ id: "c1", pos: [0.2, 0.2] as [number, number], bcs: 5 }], predators: [] },
      1000,
      false,
    );
    // Snapshot 2 at t=2000ms: cow moved to (0.8, 0.8)
    applySnapshotToTweens(
      state,
      { cows: [{ id: "c1", pos: [0.8, 0.8] as [number, number], bcs: 5 }], predators: [] },
      2000,
      false,
    );
    const rec = state.cows.get("c1");
    if (!rec) throw new Error("cow not seeded");
    // Immediately after retarget — still at 0.2
    expect(tweenValue(rec.xTween, 2000)).toBeCloseTo(0.2, 5);
    // Midway through (400ms into 800ms tween) — ease-out-cubic(0.5)=0.875
    // → 0.2 + (0.8 - 0.2) * 0.875 = 0.725
    expect(tweenValue(rec.xTween, 2400)).toBeCloseTo(0.725, 3);
    // After 800ms — at target
    expect(tweenValue(rec.xTween, 2800)).toBeCloseTo(0.8, 5);
  });

  it("prefers-reduced-motion snaps cow positions with 0ms duration", () => {
    const state = makeState();
    applySnapshotToTweens(
      state,
      { cows: [{ id: "c1", pos: [0.2, 0.2] as [number, number], bcs: 5 }], predators: [] },
      1000,
      true, // reduce motion
    );
    applySnapshotToTweens(
      state,
      { cows: [{ id: "c1", pos: [0.8, 0.8] as [number, number], bcs: 5 }], predators: [] },
      2000,
      true,
    );
    const rec = state.cows.get("c1");
    if (!rec) throw new Error("cow not seeded");
    // First sample after retarget should already be at target (snap-to).
    expect(tweenValue(rec.xTween, 2000)).toBeCloseTo(0.8, 5);
  });

  it("culls cows absent from the new snapshot", () => {
    const state = makeState();
    applySnapshotToTweens(
      state,
      {
        cows: [
          { id: "c1", pos: [0.2, 0.2] as [number, number], bcs: 5 },
          { id: "c2", pos: [0.4, 0.4] as [number, number], bcs: 5 },
        ],
        predators: [],
      },
      1000,
      false,
    );
    expect(state.cows.size).toBe(2);
    applySnapshotToTweens(
      state,
      {
        cows: [{ id: "c1", pos: [0.3, 0.3] as [number, number], bcs: 5 }],
        predators: [],
      },
      2000,
      false,
    );
    expect(state.cows.size).toBe(1);
    expect(state.cows.has("c1")).toBe(true);
    expect(state.cows.has("c2")).toBe(false);
  });

  it("triggers a color cross-fade when a cow's health state changes", () => {
    const state = makeState();
    applySnapshotToTweens(
      state,
      { cows: [{ id: "c1", pos: [0.5, 0.5] as [number, number], bcs: 5 }], predators: [] },
      1000,
      false,
    );
    const rec1 = state.cows.get("c1");
    if (!rec1) throw new Error("cow missing");
    expect(rec1.health).toBe("healthy");
    // Sick transition
    applySnapshotToTweens(
      state,
      {
        cows: [
          { id: "c1", pos: [0.5, 0.5] as [number, number], bcs: 5, state: "sick" },
        ],
        predators: [],
      },
      2000,
      false,
    );
    const rec2 = state.cows.get("c1");
    if (!rec2) throw new Error("cow missing");
    expect(rec2.health).toBe("sick");
    // colorStartMs should be the current now
    expect(rec2.colorStartMs).toBe(2000);
    // Source color is the previously-applied healthy RGB
    expect(rec2.colorFrom).toEqual([148, 176, 136]);
    expect(rec2.colorTo).toEqual([224, 100, 90]);
  });
});

describe("applySnapshotToTweens — drone + trail + predators", () => {
  it("seeds drone tween on first snapshot and retargets on subsequent", () => {
    const state = makeState();
    applySnapshotToTweens(
      state,
      { cows: [], predators: [], drone: { pos: [0.1, 0.1] as [number, number] } },
      1000,
      false,
    );
    expect(state.drone).not.toBeNull();
    applySnapshotToTweens(
      state,
      { cows: [], predators: [], drone: { pos: [0.9, 0.9] as [number, number] } },
      2000,
      false,
    );
    if (!state.drone) throw new Error("drone missing");
    // Drone tween uses 600ms duration — at 300ms into retarget,
    // ease-out-cubic(0.5) = 0.875 → 0.1 + 0.8*0.875 = 0.8
    expect(tweenValue(state.drone.xTween, 2300)).toBeCloseTo(0.8, 3);
    // After 600ms — fully at target
    expect(tweenValue(state.drone.xTween, 2600)).toBeCloseTo(0.9, 5);
  });

  it("appends a trail point each time the drone target changes", () => {
    const state = makeState();
    applySnapshotToTweens(
      state,
      { cows: [], predators: [], drone: { pos: [0.1, 0.1] as [number, number] } },
      1000,
      false,
    );
    applySnapshotToTweens(
      state,
      { cows: [], predators: [], drone: { pos: [0.5, 0.5] as [number, number] } },
      2000,
      false,
    );
    applySnapshotToTweens(
      state,
      { cows: [], predators: [], drone: { pos: [0.5, 0.5] as [number, number] } },
      3000,
      false,
    );
    expect(state.trail.length).toBe(2);
    expect(state.trail[1].spawnMs).toBe(2000);
  });

  it("caps trail at TRAIL_LEN=12 points", () => {
    const state = makeState();
    for (let i = 0; i < 30; i++) {
      applySnapshotToTweens(
        state,
        {
          cows: [],
          predators: [],
          drone: { pos: [i * 0.03, i * 0.03] as [number, number] },
        },
        1000 + i * 100,
        false,
      );
    }
    expect(state.trail.length).toBeLessThanOrEqual(12);
  });

  it("tweens new predators from their seed position with fade-in", () => {
    const state = makeState();
    applySnapshotToTweens(
      state,
      {
        cows: [],
        predators: [
          { id: "p1", pos: [0.5, 0.5] as [number, number], species: "coyote" },
        ],
      },
      1000,
      false,
    );
    const rec = state.predators.get("p1");
    expect(rec).toBeDefined();
    if (!rec) return;
    expect(rec.fadeStartMs).toBe(1000);
    expect(tweenValue(rec.xTween, 1000)).toBeCloseTo(0.5, 5);
  });
});
