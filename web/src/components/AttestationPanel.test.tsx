import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act, waitFor } from "@testing-library/react";
import { AttestationPanel } from "./AttestationPanel";

// Mock fetch to return empty entries
vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
  ok: true,
  json: () => Promise.resolve({ entries: [], ts: Date.now() / 1000 }),
}));

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

const SAMPLE_ENTRY = {
  seq: 1,
  ts_iso: "2026-04-21T12:00:00Z",
  source: "FenceLineDispatcher",
  kind: "fence.breach",
  payload_json: '{"mock":true}',
  prev_hash: "GENESIS",
  event_hash: "cafebabe00000001",
  signature: "a1b2c3d4".repeat(16),
  pubkey: "-----BEGIN PUBLIC KEY-----\nMOCK\n-----END PUBLIC KEY-----",
};

describe("AttestationPanel", () => {
  beforeEach(() => {
    sseHandlers = {};
    vi.clearAllMocks();
    // Reset fetch mock
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ entries: [], ts: Date.now() / 1000 }),
    }));
  });

  it("renders without crashing", async () => {
    await act(async () => {
      render(<AttestationPanel />);
    });
  });

  it("shows attestation chain title", async () => {
    await act(async () => {
      render(<AttestationPanel />);
    });
    expect(screen.getByText(/attestation chain/i)).toBeTruthy();
  });

  it("shows 0 entries initially", async () => {
    await act(async () => {
      render(<AttestationPanel />);
    });
    expect(screen.getByText(/0 entries/i)).toBeTruthy();
  });

  it("renders a row when attest.append SSE event arrives", async () => {
    await act(async () => {
      render(<AttestationPanel />);
    });
    act(() => {
      triggerSSE("attest.append", SAMPLE_ENTRY);
    });
    // seq 1 should appear
    expect(screen.getByText("1")).toBeTruthy();
  });

  it("renders source and kind from entry", async () => {
    await act(async () => {
      render(<AttestationPanel />);
    });
    act(() => {
      triggerSSE("attest.append", SAMPLE_ENTRY);
    });
    expect(screen.getByText("FenceLineDispatcher")).toBeTruthy();
    expect(screen.getByText("fence.breach")).toBeTruthy();
  });

  it("expands row details on click", async () => {
    await act(async () => {
      render(<AttestationPanel />);
    });
    act(() => {
      triggerSSE("attest.append", SAMPLE_ENTRY);
    });
    const seqCell = screen.getByText("1");
    const row = seqCell.closest("tr");
    expect(row).toBeTruthy();
    act(() => {
      fireEvent.click(row!);
    });
    // Signature and payload labels should now be visible
    expect(screen.getByText(/signature:/i)).toBeTruthy();
    expect(screen.getByText(/payload:/i)).toBeTruthy();
  });

  it("entry count increases with multiple entries", async () => {
    await act(async () => {
      render(<AttestationPanel />);
    });
    act(() => {
      triggerSSE("attest.append", { ...SAMPLE_ENTRY, seq: 1 });
      triggerSSE("attest.append", { ...SAMPLE_ENTRY, seq: 2, event_hash: "cafebabe00000002" });
      triggerSSE("attest.append", { ...SAMPLE_ENTRY, seq: 3, event_hash: "cafebabe00000003" });
    });
    expect(screen.getByText(/3 entries/i)).toBeTruthy();
  });

  it("collapses when collapsed prop is true", async () => {
    await act(async () => {
      render(<AttestationPanel collapsed={true} />);
    });
    // Table should not be in DOM when collapsed
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("calls onToggle when header is clicked", async () => {
    const onToggle = vi.fn();
    await act(async () => {
      render(<AttestationPanel collapsed={false} onToggle={onToggle} />);
    });
    // The toggle target is a <button> — find it by the title text inside it
    const titleEl = screen.getByText(/attestation chain/i);
    const header = titleEl.closest("button") ?? titleEl.closest("div");
    fireEvent.click(header!);
    expect(onToggle).toHaveBeenCalledOnce();
  });
});

describe("AttestationPanel — Verify Chain button (DASH-04)", () => {
  beforeEach(() => {
    sseHandlers = {};
    vi.clearAllMocks();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ entries: [], ts: Date.now() / 1000 }),
      }),
    );
  });

  it("renders a Verify button in the header initially", async () => {
    await act(async () => {
      render(<AttestationPanel />);
    });
    expect(screen.getByRole("button", { name: /verify/i })).toBeTruthy();
  });

  it("shows VALID chip after successful POST /api/attest/verify", async () => {
    const fetchFn = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      if (typeof url === "string" && url.includes("/api/attest/verify") && init?.method === "POST") {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ valid: true, total: 42 }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ entries: [], ts: Date.now() / 1000 }),
      });
    });
    vi.stubGlobal("fetch", fetchFn);

    await act(async () => {
      render(<AttestationPanel />);
    });
    const btn = screen.getByRole("button", { name: /verify/i });
    await act(async () => {
      fireEvent.click(btn);
    });

    await waitFor(() => expect(screen.getByText(/VALID/)).toBeTruthy());
    // Confirm POST method was used
    const postCall = fetchFn.mock.calls.find(
      (c: unknown[]) => typeof c[0] === "string" && (c[0] as string).includes("/api/attest/verify"),
    );
    expect(postCall).toBeTruthy();
    expect((postCall as [string, RequestInit])[1]?.method).toBe("POST");
  });

  it("shows INVALID chip when verify returns valid:false", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string, init?: RequestInit) => {
        if (
          typeof url === "string" &&
          url.includes("/api/attest/verify") &&
          init?.method === "POST"
        ) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                valid: false,
                total: 42,
                first_bad_seq: 17,
                reason: "hash mismatch",
              }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ entries: [], ts: Date.now() / 1000 }),
        });
      }),
    );

    await act(async () => {
      render(<AttestationPanel />);
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /verify/i }));
    });
    await waitFor(() => expect(screen.getByText(/INVALID/)).toBeTruthy());
  });
});
