import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { ScenarioBanner } from "../ScenarioBanner";

let sseHandlers: Record<string, ((payload: unknown) => void)[]> = {};

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

function emit(eventType: string, payload: unknown) {
  (sseHandlers[eventType] ?? []).forEach((h) => h(payload));
}

describe("ScenarioBanner", () => {
  beforeEach(() => {
    sseHandlers = {};
  });

  it("mounts showing standing-by state", async () => {
    await act(async () => {
      render(<ScenarioBanner />);
    });
    expect(screen.getByTestId("banner-idle").textContent).toMatch(/Standing by/i);
  });

  it("shows coyote headline on scenario.active", async () => {
    await act(async () => {
      render(<ScenarioBanner />);
    });
    act(() => {
      emit("scenario.active", { name: "coyote" });
    });
    expect(screen.getByTestId("banner-headline").textContent).toMatch(
      /Coyote detected/i,
    );
  });

  it("shows attested state on scenario.ended", async () => {
    vi.useFakeTimers();
    await act(async () => {
      render(<ScenarioBanner />);
    });
    act(() => {
      emit("scenario.active", { name: "coyote" });
    });
    act(() => {
      emit("scenario.ended", { name: "coyote" });
    });
    expect(screen.getByTestId("banner-headline").textContent).toMatch(
      /coyote · attested/i,
    );
    vi.useRealTimers();
  });
});
