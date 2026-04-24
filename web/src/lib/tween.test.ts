import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  easeOutCubic,
  lerp,
  createTween,
  tweenValue,
  retarget,
  lerpRgb,
  prefersReducedMotion,
  type TweenState,
} from "./tween";

describe("easeOutCubic", () => {
  it("returns 0 at t=0", () => {
    expect(easeOutCubic(0)).toBe(0);
  });

  it("returns 1 at t=1", () => {
    expect(easeOutCubic(1)).toBe(1);
  });

  it("returns 0.875 at t=0.5", () => {
    // 1 - (1-0.5)^3 = 1 - 0.125 = 0.875
    expect(easeOutCubic(0.5)).toBeCloseTo(0.875, 5);
  });

  it("clamps input to [0,1]", () => {
    expect(easeOutCubic(-0.5)).toBe(0);
    expect(easeOutCubic(1.5)).toBe(1);
  });

  it("is monotonic over [0,1]", () => {
    let prev = -Infinity;
    for (let i = 0; i <= 20; i++) {
      const t = i / 20;
      const v = easeOutCubic(t);
      expect(v).toBeGreaterThanOrEqual(prev);
      prev = v;
    }
  });
});

describe("lerp", () => {
  it("returns a at t=0", () => {
    expect(lerp(5, 10, 0)).toBe(5);
  });

  it("returns b at t=1", () => {
    expect(lerp(5, 10, 1)).toBe(10);
  });

  it("returns midpoint at t=0.5", () => {
    expect(lerp(5, 10, 0.5)).toBe(7.5);
  });
});

describe("createTween + tweenValue", () => {
  it("returns start value when nowMs === startMs", () => {
    const t: TweenState = createTween(0, 1, 1000, 800);
    expect(tweenValue(t, 1000)).toBe(0);
  });

  it("returns target value when nowMs >= startMs + durationMs", () => {
    const t: TweenState = createTween(0, 1, 1000, 800);
    expect(tweenValue(t, 1800)).toBe(1);
    expect(tweenValue(t, 9999)).toBe(1);
  });

  it("returns eased interior value at half progress", () => {
    const t: TweenState = createTween(0, 10, 1000, 800);
    // At t=0.5 raw progress, ease-out-cubic = 0.875 → value = 8.75
    expect(tweenValue(t, 1400)).toBeCloseTo(8.75, 5);
  });

  it("returns target immediately when durationMs is 0 (instant snap)", () => {
    const t: TweenState = createTween(0, 1, 1000, 0);
    expect(tweenValue(t, 1000)).toBe(1);
  });
});

describe("retarget", () => {
  it("preserves current display value as new start", () => {
    const t: TweenState = createTween(0, 10, 1000, 800);
    // Midway through
    const midDisplay = tweenValue(t, 1400); // ≈ 8.75
    const retargeted = retarget(t, 20, 1400);
    expect(retargeted.start).toBeCloseTo(midDisplay, 5);
    expect(retargeted.target).toBe(20);
    expect(retargeted.tweenStartMs).toBe(1400);
  });

  it("does not mutate original state", () => {
    const t: TweenState = createTween(0, 10, 1000, 800);
    const r = retarget(t, 20, 1400);
    expect(t.target).toBe(10);
    expect(t.tweenStartMs).toBe(1000);
    expect(r).not.toBe(t);
  });

  it("keeps same durationMs by default", () => {
    const t: TweenState = createTween(0, 10, 1000, 800);
    const r = retarget(t, 20, 1400);
    expect(r.durationMs).toBe(800);
  });

  it("accepts a custom durationMs override", () => {
    const t: TweenState = createTween(0, 10, 1000, 800);
    const r = retarget(t, 20, 1400, 1200);
    expect(r.durationMs).toBe(1200);
  });
});

describe("lerpRgb", () => {
  it("returns start color as rgba at t=0", () => {
    expect(lerpRgb([255, 0, 0], [0, 0, 255], 0, 1)).toBe("rgba(255,0,0,1)");
  });

  it("returns end color as rgba at t=1", () => {
    expect(lerpRgb([255, 0, 0], [0, 0, 255], 1, 1)).toBe("rgba(0,0,255,1)");
  });

  it("blends linearly at midpoint", () => {
    // Should be roughly (128, 0, 128)
    const result = lerpRgb([255, 0, 0], [0, 0, 255], 0.5, 0.8);
    const match = result.match(/rgba\((\d+),(\d+),(\d+),([\d.]+)\)/);
    expect(match).toBeTruthy();
    if (match) {
      expect(parseInt(match[1], 10)).toBeGreaterThanOrEqual(126);
      expect(parseInt(match[1], 10)).toBeLessThanOrEqual(129);
      expect(parseInt(match[3], 10)).toBeGreaterThanOrEqual(126);
      expect(parseInt(match[3], 10)).toBeLessThanOrEqual(129);
      expect(parseFloat(match[4])).toBeCloseTo(0.8, 2);
    }
  });

  it("clamps t to [0,1]", () => {
    expect(lerpRgb([255, 0, 0], [0, 0, 255], -1, 1)).toBe("rgba(255,0,0,1)");
    expect(lerpRgb([255, 0, 0], [0, 0, 255], 2, 1)).toBe("rgba(0,0,255,1)");
  });

  it("rounds integer channel values", () => {
    const result = lerpRgb([10, 20, 30], [40, 50, 60], 0.333, 1);
    const match = result.match(/rgba\((\d+),(\d+),(\d+),([\d.]+)\)/);
    expect(match).toBeTruthy();
    // Values should be integers (no decimals in channels)
    if (match) {
      expect(match[1]).not.toContain(".");
      expect(match[2]).not.toContain(".");
      expect(match[3]).not.toContain(".");
    }
  });
});

describe("prefersReducedMotion", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns false when matchMedia is unavailable", () => {
    const original = window.matchMedia;
    // @ts-expect-error — test-only override
    delete window.matchMedia;
    expect(prefersReducedMotion()).toBe(false);
    window.matchMedia = original;
  });

  it("returns true when media query matches", () => {
    vi.spyOn(window, "matchMedia").mockImplementation(
      (q: string) =>
        ({
          matches: q.includes("prefers-reduced-motion"),
          media: q,
          addEventListener: () => {},
          removeEventListener: () => {},
          addListener: () => {},
          removeListener: () => {},
          dispatchEvent: () => false,
          onchange: null,
        }) as unknown as MediaQueryList,
    );
    expect(prefersReducedMotion()).toBe(true);
  });

  it("returns false when media query does not match", () => {
    vi.spyOn(window, "matchMedia").mockImplementation(
      (q: string) =>
        ({
          matches: false,
          media: q,
          addEventListener: () => {},
          removeEventListener: () => {},
          addListener: () => {},
          removeListener: () => {},
          dispatchEvent: () => false,
          onchange: null,
        }) as unknown as MediaQueryList,
    );
    expect(prefersReducedMotion()).toBe(false);
  });
});

describe("integration — retarget mid-flight stays continuous", () => {
  it("display value is continuous across a retarget event", () => {
    const t0 = createTween(0, 100, 1000, 800);
    const midDisplay = tweenValue(t0, 1400); // ≈ 87.5
    const t1 = retarget(t0, 50, 1400);
    // First sample of new tween at the same nowMs should equal midDisplay
    expect(tweenValue(t1, 1400)).toBeCloseTo(midDisplay, 5);
  });
});
