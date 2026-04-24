/**
 * LaptopDroneControl tests (Phase 7.1 LDC-02 + LDC-06).
 *
 * Covers:
 *   - Panel hidden by default (window.__DRONE_MANUAL_ENABLED falsy).
 *   - 6 action buttons when enabled.
 *   - State chips from /api/snapshot polling.
 *   - Hold-to-fire 3s for ARM; immediate fire for DISARM.
 *   - X-Manual-Override-Token header on POST.
 *   - Action log updated by drone.manual_override SSE.
 *   - Error chip on 401 response.
 *   - ARIA labels present for hold vs immediate buttons.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, act, waitFor } from "@testing-library/react";
import { LaptopDroneControl } from "./LaptopDroneControl";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let sseHandlers: Record<string, Array<(payload: any) => void>> = {};
let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  sseHandlers = {};
  fetchMock = vi.fn().mockImplementation((url: string) => {
    if (typeof url === "string" && url === "/api/snapshot") {
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            drone: {
              lat: 34.123,
              lon: -106.456,
              alt_m: 12.5,
              state: "idle",
              battery_pct: 78,
            },
          }),
      } as Response);
    }
    // All /api/drone/* return 200 by default.
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () =>
        Promise.resolve({
          ok: true,
          action: typeof url === "string" ? url.split("/").pop() : "",
          latency_ms: 4,
        }),
    } as Response);
  });
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  // Clean up window state between tests.
  if (typeof window !== "undefined") {
    delete window.__DRONE_MANUAL_ENABLED;
    delete window.__DRONE_MANUAL_TOKEN;
  }
});

vi.mock("@/lib/sse", () => ({
  getSSE: () => ({
    on: (eventType: string, handler: (payload: unknown) => void) => {
      if (!sseHandlers[eventType]) sseHandlers[eventType] = [];
      sseHandlers[eventType].push(handler);
    },
    off: (eventType: string, handler: (payload: unknown) => void) => {
      sseHandlers[eventType] = (sseHandlers[eventType] ?? []).filter(
        (h) => h !== handler,
      );
    },
  }),
}));

function triggerSSE(eventType: string, payload: unknown) {
  (sseHandlers[eventType] ?? []).forEach((h) => h(payload));
}

describe("LaptopDroneControl — disabled by default", () => {
  it("renders the disabled placeholder when window.__DRONE_MANUAL_ENABLED is absent", async () => {
    await act(async () => {
      render(<LaptopDroneControl />);
    });
    expect(
      screen.queryByTestId("laptop-drone-panel-disabled"),
    ).not.toBeNull();
    expect(screen.queryByTestId("laptop-drone-panel")).toBeNull();
  });
});

describe("LaptopDroneControl — enabled", () => {
  it("renders all 6 action buttons when enabled", async () => {
    await act(async () => {
      render(<LaptopDroneControl forceEnabled />);
    });
    const actions = ["arm", "disarm", "takeoff", "rtl", "land", "estop"];
    for (const a of actions) {
      expect(screen.getByTestId(`drone-btn-${a}`)).toBeTruthy();
    }
  });

  it("renders state chips fetched from /api/snapshot", async () => {
    await act(async () => {
      render(<LaptopDroneControl forceEnabled />);
    });
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/snapshot");
    });
    await waitFor(() => {
      expect(screen.getByTestId("chip-gps").textContent).toContain("lock");
      expect(screen.getByTestId("chip-alt").textContent).toContain("12.5");
      expect(screen.getByTestId("chip-mode").textContent).toContain("idle");
    });
  });

  it("ARM button requires 3s hold before POST fires", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: false });
    // `performance.now()` in jsdom needs manual advancement alongside timers.
    const nowSpy = vi.spyOn(performance, "now");
    let nowValue = 0;
    nowSpy.mockImplementation(() => nowValue);

    await act(async () => {
      render(<LaptopDroneControl forceEnabled token="test-token" />);
    });
    const armBtn = screen.getByTestId("drone-btn-arm");
    act(() => {
      fireEvent.pointerDown(armBtn);
    });

    // Advance 1 second — well before hold completes.
    nowValue = 1000;
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    const droneArmCalls = fetchMock.mock.calls.filter(
      ([url]) => url === "/api/drone/arm",
    );
    expect(droneArmCalls.length).toBe(0);

    // Advance to 3000ms — hold completes, fire should happen.
    nowValue = 3050;
    act(() => {
      vi.advanceTimersByTime(2050);
    });

    vi.useRealTimers();
    nowSpy.mockRestore();
    await waitFor(() => {
      const calls = fetchMock.mock.calls.filter(
        ([url]) => url === "/api/drone/arm",
      );
      expect(calls.length).toBe(1);
    });
  });

  it("DISARM fires immediately with no hold required", async () => {
    await act(async () => {
      render(<LaptopDroneControl forceEnabled token="test-token" />);
    });
    const disarmBtn = screen.getByTestId("drone-btn-disarm");
    act(() => {
      fireEvent.pointerDown(disarmBtn);
    });
    await waitFor(() => {
      const calls = fetchMock.mock.calls.filter(
        ([url]) => url === "/api/drone/disarm",
      );
      expect(calls.length).toBe(1);
    });
  });

  it("sends X-Manual-Override-Token header", async () => {
    await act(async () => {
      render(<LaptopDroneControl forceEnabled token="secret-123" />);
    });
    act(() => {
      fireEvent.pointerDown(screen.getByTestId("drone-btn-rtl"));
    });
    await waitFor(() => {
      const rtlCall = fetchMock.mock.calls.find(
        ([url]) => url === "/api/drone/rtl",
      );
      expect(rtlCall).toBeDefined();
      const init = rtlCall![1] as RequestInit;
      expect(init.method).toBe("POST");
      const headers = init.headers as Record<string, string>;
      expect(headers["X-Manual-Override-Token"]).toBe("secret-123");
    });
  });

  it("updates action history on drone.manual_override SSE", async () => {
    await act(async () => {
      render(<LaptopDroneControl forceEnabled />);
    });
    act(() =>
      triggerSSE("drone.manual_override", {
        action: "rtl",
        actor: "laptop",
        ts: 1_700_000_000,
        success: true,
        latency_ms: 12,
      }),
    );
    await waitFor(() => {
      expect(screen.queryByTestId("log-row-rtl")).not.toBeNull();
    });
  });

  it("shows error chip on 401 response", async () => {
    // Override the default mock to return 401 on arm.
    fetchMock.mockImplementation((url: string) => {
      if (url === "/api/snapshot") {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ drone: { state: "idle" } }),
        } as Response);
      }
      if (url === "/api/drone/disarm") {
        return Promise.resolve({
          ok: false,
          status: 401,
          json: () => Promise.resolve({ detail: "missing token" }),
        } as Response);
      }
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) } as Response);
    });

    await act(async () => {
      render(<LaptopDroneControl forceEnabled token="" />);
    });
    act(() => {
      fireEvent.pointerDown(screen.getByTestId("drone-btn-disarm"));
    });

    await waitFor(() => {
      const btn = screen.getByTestId("drone-btn-disarm");
      // The sr-only alert carries the "401: missing token" text.
      expect(btn.textContent ?? "").not.toBe("");
      // The error shows up in the button's aria-describedby target.
      const errId = btn.getAttribute("aria-describedby");
      expect(errId).toBeTruthy();
      const errEl = document.getElementById(errId!);
      expect(errEl?.textContent).toContain("401");
    });
  });

  it("ARIA: each button has aria-label describing hold-to-fire or immediate", async () => {
    await act(async () => {
      render(<LaptopDroneControl forceEnabled />);
    });
    // Hold-to-fire buttons.
    expect(screen.getByTestId("drone-btn-arm").getAttribute("aria-label")).toMatch(/hold/i);
    expect(
      screen.getByTestId("drone-btn-takeoff").getAttribute("aria-label"),
    ).toMatch(/hold/i);
    expect(
      screen.getByTestId("drone-btn-estop").getAttribute("aria-label"),
    ).toMatch(/hold/i);
    // Immediate buttons.
    expect(
      screen.getByTestId("drone-btn-disarm").getAttribute("aria-label"),
    ).toMatch(/click/i);
    expect(
      screen.getByTestId("drone-btn-rtl").getAttribute("aria-label"),
    ).toMatch(/click/i);
    expect(
      screen.getByTestId("drone-btn-land").getAttribute("aria-label"),
    ).toMatch(/click/i);
  });
});
