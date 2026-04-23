import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { AttestChainViewer } from "./AttestChainViewer";

const SAMPLE_CHAIN = [
  {
    seq: 1,
    ts_iso: "2026-04-23T10:00:00Z",
    source: "sensor.water.1",
    kind: "water.low",
    payload_json: '{"tank":1}',
    prev_hash: "GENESIS",
    event_hash: "aaaa0000",
    signature: "sig1",
    pubkey: "-----BEGIN PUBLIC KEY-----\nm\n-----END PUBLIC KEY-----",
  },
  {
    seq: 2,
    ts_iso: "2026-04-23T10:00:01Z",
    source: "memory",
    kind: "memver.written",
    payload_json: '{"_memver_id":"memver_x"}',
    prev_hash: "aaaa0000",
    event_hash: "bbbb0000",
    signature: "sig2",
    pubkey: "-----BEGIN PUBLIC KEY-----\nm\n-----END PUBLIC KEY-----",
  },
  {
    seq: 3,
    ts_iso: "2026-04-23T10:00:02Z",
    source: "sensor.fence",
    kind: "fence.breach",
    payload_json: '{"fence":"n"}',
    prev_hash: "bbbb0000",
    event_hash: "cccc0000",
    signature: "sig3",
    pubkey: "-----BEGIN PUBLIC KEY-----\nm\n-----END PUBLIC KEY-----",
  },
];

function mockFetchFor(hash: string, verifyValid = true, notFound = false) {
  return vi.fn().mockImplementation((url: string, init?: RequestInit) => {
    if (url.startsWith("/api/attest/by-hash/")) {
      if (notFound) {
        return Promise.resolve({
          ok: false,
          status: 404,
          json: () => Promise.resolve({ detail: "not found" }),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({ target: hash, chain: SAMPLE_CHAIN, ts: 1 }),
      });
    }
    if (url === "/api/attest/verify" && init?.method === "POST") {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            valid: verifyValid,
            total: SAMPLE_CHAIN.length,
            first_bad_seq: verifyValid ? null : 2,
            reason: verifyValid ? null : "tampered",
          }),
      });
    }
    return Promise.reject(new Error(`unexpected fetch: ${url}`));
  });
}

describe("AttestChainViewer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading then chain with 3 rows", async () => {
    vi.stubGlobal("fetch", mockFetchFor("cccc0000", true));
    render(<AttestChainViewer hash="cccc0000" />);
    expect(screen.getByTestId("viewer-loading")).toBeDefined();
    await waitFor(() => expect(screen.getByTestId("viewer-chain")).toBeDefined());
    expect(screen.getByTestId("viewer-row-1")).toBeDefined();
    expect(screen.getByTestId("viewer-row-2")).toBeDefined();
    expect(screen.getByTestId("viewer-row-3")).toBeDefined();
  });

  it("shows target hash in header", async () => {
    vi.stubGlobal("fetch", mockFetchFor("cccc0000", true));
    render(<AttestChainViewer hash="cccc0000" />);
    await waitFor(() => expect(screen.getByTestId("viewer-chain")).toBeDefined());
    expect(screen.getByTestId("viewer-target-hash").textContent).toContain(
      "cccc0000",
    );
  });

  it("marks all rows verified when chain is valid", async () => {
    vi.stubGlobal("fetch", mockFetchFor("cccc0000", true));
    render(<AttestChainViewer hash="cccc0000" />);
    await waitFor(() => {
      const s1 = screen.getByTestId("verify-status-1");
      expect(s1.textContent).toContain("✓");
    });
    expect(screen.getByTestId("verify-status-2").textContent).toContain("✓");
    expect(screen.getByTestId("verify-status-3").textContent).toContain("✓");
  });

  it("marks first_bad_seq as Invalid and preceding rows as Verified", async () => {
    vi.stubGlobal("fetch", mockFetchFor("cccc0000", false));
    render(<AttestChainViewer hash="cccc0000" />);
    await waitFor(() => {
      const s = screen.getByTestId("verify-status-2");
      expect(s.textContent).toContain("✗");
    });
    // seq=1 is before first_bad_seq → ✓; seq=3 is after → pending
    expect(screen.getByTestId("verify-status-1").textContent).toContain("✓");
  });

  it("renders not-found message on 404", async () => {
    vi.stubGlobal("fetch", mockFetchFor("unknown", true, true));
    render(<AttestChainViewer hash="unknown" />);
    await waitFor(() => expect(screen.getByTestId("viewer-not-found")).toBeDefined());
  });

  it("renders error message when network fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("network down")),
    );
    render(<AttestChainViewer hash="abc" />);
    await waitFor(() => expect(screen.getByTestId("viewer-error")).toBeDefined());
  });
});
