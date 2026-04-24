/**
 * SkyHerdReplay — opt-in start/pause behaviour (Phase 3.1).
 *
 * A fresh instance must be paused. start() kicks the loop; pause() halts it.
 * No events flow to listeners while paused. Uses fake timers so the test is
 * deterministic and fast.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { SkyHerdReplay } from "../replay";

// Minimal replay.json payload — one scenario, two events close in time.
const FAKE_BUNDLE = {
  scenarios: [
    {
      name: "coyote",
      duration_s: 10,
      events: [
        { ts_rel: 0.1, kind: "fence.breach", payload: { fence_id: "F-01", species_hint: "coyote" } },
        { ts_rel: 0.2, kind: "agent.log", payload: { agent: "FenceLineDispatcher", msg: "test" } },
      ],
    },
  ],
};

function mockFetchOnce(bundle: unknown): void {
  const resp = {
    ok: true,
    status: 200,
    json: async () => bundle,
  };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (globalThis as any).fetch = vi.fn(async () => resp as unknown as Response);
}

describe("SkyHerdReplay — paused-by-default", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockFetchOnce(FAKE_BUNDLE);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("new instance is paused by default", () => {
    const r = new SkyHerdReplay();
    expect(r.isPaused()).toBe(true);
  });

  it("does not emit events before start() is called", async () => {
    const r = new SkyHerdReplay();
    const handler = vi.fn();
    r.on("fence.breach", handler);

    // Advance wall-clock well past when the first event would fire.
    await vi.advanceTimersByTimeAsync(5000);

    expect(handler).not.toHaveBeenCalled();
    expect(r.isPaused()).toBe(true);
  });

  it("start() unpauses and emits events", async () => {
    const r = new SkyHerdReplay();
    const handler = vi.fn();
    r.on("fence.breach", handler);

    r.start();
    expect(r.isPaused()).toBe(false);

    // Let the fetch microtask resolve, then advance past the first event's scheduled offset.
    await vi.advanceTimersByTimeAsync(2000);

    expect(handler).toHaveBeenCalled();
  });

  it("pause() halts subsequent emission", async () => {
    const r = new SkyHerdReplay();
    const handler = vi.fn();
    r.on("fence.breach", handler);

    r.start();
    r.pause();
    expect(r.isPaused()).toBe(true);

    await vi.advanceTimersByTimeAsync(2000);

    expect(handler).not.toHaveBeenCalled();
  });

  it("start() after pause() re-emits events (resumable)", async () => {
    const r = new SkyHerdReplay();
    const handler = vi.fn();
    r.on("fence.breach", handler);

    r.start();
    r.pause();
    await vi.advanceTimersByTimeAsync(2000);
    expect(handler).not.toHaveBeenCalled();

    // Restart from scratch — simplest resume semantics.
    r.start();
    await vi.advanceTimersByTimeAsync(2000);

    expect(handler).toHaveBeenCalled();
  });
});
