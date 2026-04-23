/**
 * MemoryPanel tests (Plan 01-06):
 *   - 5 agent tabs rendered
 *   - /api/memory/{agent} fetched on mount + tab switch
 *   - memory.written SSE prepends entry + flash
 *   - HashChip appears for each row
 *   - Dedupe by memory_version_id
 *   - SSE handler registered/unregistered on mount/unmount
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act, waitFor } from "@testing-library/react";
import { MemoryPanel } from "./MemoryPanel";

let fetchMock: ReturnType<typeof vi.fn>;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let sseHandlers: Record<string, Array<(payload: any) => void>> = {};

beforeEach(() => {
  sseHandlers = {};
  fetchMock = vi.fn().mockImplementation((url: string) => {
    // Only seed entries for FenceLineDispatcher; other agents start empty so
    // the dedupe test can assert exactly one SSE-pushed row.
    const isFLD = typeof url === "string" && url.endsWith("FenceLineDispatcher");
    const entries = isFLD
      ? [
          {
            memory_id: "mem_seed_01234567",
            memory_version_id: "memver_01XRSVdKC1McTbhVbVF5T47E",
            memory_store_id: "memstore_01FLD23456789",
            path: "/patterns/seed.md",
            content_sha256: "a".repeat(64),
            content_size_bytes: 64,
            created_at: "1970-01-01T00:00:00Z",
            operation: "created",
          },
        ]
      : [];
    return Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          agent: isFLD ? "FenceLineDispatcher" : url.split("/").pop(),
          entries,
          ts: 0,
          _url: url,
        }),
    } as Response);
  });
  vi.stubGlobal("fetch", fetchMock);
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

const SAMPLE_WRITTEN = {
  agent: "PredatorPatternLearner",
  memory_store_id: "memstore_01PPL23456789",
  memory_id: "mem_new_0123456789",
  memory_version_id: "memver_02NEW4K5L6McTbhVbVF5T47F",
  content_sha256: "b".repeat(64),
  path: "/patterns/coyote-crossings.md",
};

describe("MemoryPanel", () => {
  it("renders all 5 agent tabs", async () => {
    await act(async () => {
      render(<MemoryPanel />);
    });
    for (const name of [
      "FenceLineDispatcher",
      "HerdHealthWatcher",
      "PredatorPatternLearner",
      "GrazingOptimizer",
      "CalvingWatch",
    ]) {
      expect(screen.getByTestId(`memory-tab-${name}`)).toBeTruthy();
    }
  });

  it("fetches /api/memory/{agent} on mount", async () => {
    await act(async () => {
      render(<MemoryPanel />);
    });
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith("/api/memory/FenceLineDispatcher"),
    );
  });

  it("switches fetch URL on tab change", async () => {
    await act(async () => {
      render(<MemoryPanel />);
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("memory-tab-HerdHealthWatcher"));
    });
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith("/api/memory/HerdHealthWatcher"),
    );
  });

  it("prepends memory.written SSE event to the matching agent's feed", async () => {
    await act(async () => {
      render(<MemoryPanel />);
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("memory-tab-PredatorPatternLearner"));
    });
    act(() => triggerSSE("memory.written", SAMPLE_WRITTEN));
    await waitFor(() => {
      const rows = document.querySelectorAll("[data-testid='memory-row']");
      expect(rows.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("renders HashChip for each memver row", async () => {
    await act(async () => {
      render(<MemoryPanel />);
    });
    await waitFor(() => {
      const chips = document.querySelectorAll("[data-testid='hash-chip']");
      expect(chips.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("deduplicates entries by memory_version_id", async () => {
    await act(async () => {
      render(<MemoryPanel />);
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("memory-tab-PredatorPatternLearner"));
    });
    act(() => triggerSSE("memory.written", SAMPLE_WRITTEN));
    act(() => triggerSSE("memory.written", SAMPLE_WRITTEN));
    await waitFor(() => {
      const rows = document.querySelectorAll("[data-testid='memory-row']");
      expect(rows.length).toBe(1);
    });
  });

  it("registers and unregisters memory.written handler on mount/unmount", async () => {
    const { unmount } = render(<MemoryPanel />);
    await waitFor(() =>
      expect((sseHandlers["memory.written"] ?? []).length).toBe(1),
    );
    await act(async () => {
      unmount();
    });
    expect((sseHandlers["memory.written"] ?? []).length).toBe(0);
  });
});
