/**
 * CrossRanchPanel tests (Phase 02 CRM-04/05/06):
 *   - Renders inbound/outbound headers
 *   - Fetches /api/neighbors on mount
 *   - Populates rows from initial fetch
 *   - neighbor.alert SSE prepends as inbound
 *   - neighbor.handoff SSE prepends as outbound
 *   - Deduplicates by composite key
 *   - Registers/unregisters both SSE handlers on mount/unmount
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act, waitFor } from "@testing-library/react";
import { CrossRanchPanel } from "./CrossRanchPanel";

let fetchMock: ReturnType<typeof vi.fn>;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let sseHandlers: Record<string, Array<(payload: any) => void>> = {};

const SEED_INBOUND = {
  direction: "inbound" as const,
  from_ranch: "ranch_a",
  to_ranch: "ranch_b",
  species: "coyote",
  shared_fence: "fence_west",
  confidence: 0.91,
  ts: 1745200000,
  attestation_hash: "sha256:seedin",
};

const SEED_OUTBOUND = {
  direction: "outbound" as const,
  from_ranch: "ranch_b",
  to_ranch: "ranch_a",
  species: "coyote",
  shared_fence: "fence_east",
  confidence: 0.87,
  ts: 1745199900,
  attestation_hash: "sha256:seedout",
};

beforeEach(() => {
  sseHandlers = {};
  fetchMock = vi.fn().mockImplementation(() =>
    Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          entries: [SEED_INBOUND, SEED_OUTBOUND],
          ts: 0,
        }),
    } as Response),
  );
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

describe("CrossRanchPanel", () => {
  it("renders INBOUND and OUTBOUND table labels", async () => {
    await act(async () => {
      render(<CrossRanchPanel />);
    });
    expect(screen.getAllByText(/INBOUND/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/OUTBOUND/i).length).toBeGreaterThanOrEqual(1);
  });

  it("fetches /api/neighbors on mount", async () => {
    await act(async () => {
      render(<CrossRanchPanel />);
    });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/neighbors"));
  });

  it("populates rows from initial fetch response", async () => {
    await act(async () => {
      render(<CrossRanchPanel />);
    });
    await waitFor(() => {
      const rows = document.querySelectorAll("[data-testid='neighbor-row']");
      expect(rows.length).toBe(2);
    });
  });

  it("prepends neighbor.alert SSE event as an inbound row", async () => {
    // Empty initial fetch
    fetchMock.mockImplementationOnce(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ entries: [], ts: 0 }),
      } as Response),
    );
    await act(async () => {
      render(<CrossRanchPanel />);
    });
    act(() => {
      triggerSSE("neighbor.alert", {
        from_ranch: "ranch_c",
        to_ranch: "ranch_b",
        species: "mountain_lion",
        shared_fence: "fence_south",
        confidence: 0.77,
        ts: 1745200010,
        attestation_hash: "sha256:alert1",
      });
    });
    await waitFor(() => {
      const rows = document.querySelectorAll("[data-testid='neighbor-row']");
      expect(rows.length).toBe(1);
    });
  });

  it("prepends neighbor.handoff SSE event as an outbound row", async () => {
    fetchMock.mockImplementationOnce(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ entries: [], ts: 0 }),
      } as Response),
    );
    await act(async () => {
      render(<CrossRanchPanel />);
    });
    act(() => {
      triggerSSE("neighbor.handoff", {
        from_ranch: "ranch_b",
        to_ranch: "ranch_a",
        species: "coyote",
        shared_fence: "fence_east",
        confidence: 0.82,
        ts: 1745200020,
        attestation_hash: "sha256:handoff1",
      });
    });
    await waitFor(() => {
      const rows = document.querySelectorAll("[data-testid='neighbor-row']");
      expect(rows.length).toBe(1);
    });
  });

  it("deduplicates by composite key (direction, from, to, fence, ts)", async () => {
    fetchMock.mockImplementationOnce(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ entries: [], ts: 0 }),
      } as Response),
    );
    await act(async () => {
      render(<CrossRanchPanel />);
    });
    const same = {
      from_ranch: "ranch_a",
      to_ranch: "ranch_b",
      species: "coyote",
      shared_fence: "fence_west",
      confidence: 0.91,
      ts: 1745200099,
      attestation_hash: "sha256:dedupe",
    };
    act(() => triggerSSE("neighbor.alert", same));
    act(() => triggerSSE("neighbor.alert", same));
    await waitFor(() => {
      const rows = document.querySelectorAll("[data-testid='neighbor-row']");
      expect(rows.length).toBe(1);
    });
  });

  it("registers and unregisters both SSE handlers on mount/unmount", async () => {
    const { unmount } = render(<CrossRanchPanel />);
    await waitFor(() =>
      expect((sseHandlers["neighbor.alert"] ?? []).length).toBe(1),
    );
    await waitFor(() =>
      expect((sseHandlers["neighbor.handoff"] ?? []).length).toBe(1),
    );
    await act(async () => {
      unmount();
    });
    expect((sseHandlers["neighbor.alert"] ?? []).length).toBe(0);
    expect((sseHandlers["neighbor.handoff"] ?? []).length).toBe(0);
  });
});
