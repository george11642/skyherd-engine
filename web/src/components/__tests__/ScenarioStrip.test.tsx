/**
 * ScenarioStrip — Start Simulation overlay (Phase 3.3).
 *
 * Separate from the legacy sibling test (shared/ScenarioStrip.test.tsx) which
 * covers the pill SSE behaviour. This file focuses on overlay visibility,
 * keyboard activation, and the replay.start() contract.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ScenarioStrip } from "../shared/ScenarioStrip";

// Stub getSSE so useEffect on/off doesn't explode.
vi.mock("@/lib/sse", async () => {
  const actual = await vi.importActual<typeof import("@/lib/sse")>("@/lib/sse");
  return {
    ...actual,
    getSSE: () => ({
      on: () => {},
      off: () => {},
    }),
    // getReplayIfActive is exercised only when no prop is passed; the tests
    // below always pass the replay explicitly, so we return null here.
    getReplayIfActive: () => null,
  };
});

interface FakeReplay {
  start: ReturnType<typeof vi.fn>;
  pause: ReturnType<typeof vi.fn>;
  isPaused: ReturnType<typeof vi.fn>;
}

function makeReplay(initialPaused = true): FakeReplay {
  let paused = initialPaused;
  return {
    start: vi.fn(() => {
      paused = false;
    }),
    pause: vi.fn(() => {
      paused = true;
    }),
    isPaused: vi.fn(() => paused),
  };
}

describe("ScenarioStrip — Start Simulation overlay", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the overlay button when replay is paused (replay mode active)", () => {
    const replay = makeReplay(true);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    render(<ScenarioStrip replay={replay as any} />);

    const btn = screen.getByRole("button", { name: /start simulation/i });
    expect(btn).toBeInTheDocument();
    expect(btn.tagName).toBe("BUTTON");
  });

  it("overlay button is focusable (keyboard reachable)", () => {
    const replay = makeReplay(true);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    render(<ScenarioStrip replay={replay as any} />);

    const btn = screen.getByRole("button", { name: /start simulation/i });
    btn.focus();
    expect(document.activeElement).toBe(btn);
  });

  it("clicking the overlay calls replay.start() exactly once and hides the overlay", () => {
    const replay = makeReplay(true);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    render(<ScenarioStrip replay={replay as any} />);

    const btn = screen.getByRole("button", { name: /start simulation/i });
    fireEvent.click(btn);

    expect(replay.start).toHaveBeenCalledTimes(1);
    // Overlay is gone; the remaining buttons are the 8 scenario pills.
    expect(screen.queryByRole("button", { name: /start simulation/i })).toBeNull();
  });

  it("announces 'Simulation started' via aria-live region after click", () => {
    const replay = makeReplay(true);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    render(<ScenarioStrip replay={replay as any} />);

    fireEvent.click(screen.getByRole("button", { name: /start simulation/i }));

    const live = screen.getByRole("status");
    expect(live).toHaveTextContent(/simulation started/i);
  });

  it("overlay does not render when no replay is provided (live SSE mode)", () => {
    render(<ScenarioStrip replay={null} />);
    expect(screen.queryByRole("button", { name: /start simulation/i })).toBeNull();
  });

  it("overlay does not render when replay is already playing (not paused)", () => {
    const replay = makeReplay(false);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    render(<ScenarioStrip replay={replay as any} />);

    expect(screen.queryByRole("button", { name: /start simulation/i })).toBeNull();
  });
});
