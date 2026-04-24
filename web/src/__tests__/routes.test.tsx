/**
 * resolveRoute — pure pathname → component-key mapping.
 * Phase 2 + Phase 5 — TDD RED before implementation.
 */
import { describe, it, expect } from "vitest";
import { resolveRoute } from "@/routes";

describe("resolveRoute", () => {
  it("maps / to landing", () => {
    expect(resolveRoute("/")).toEqual({ kind: "landing" });
  });

  it("maps /demo to dashboard (App)", () => {
    expect(resolveRoute("/demo")).toEqual({ kind: "app" });
  });

  it("preserves /rancher", () => {
    expect(resolveRoute("/rancher")).toEqual({ kind: "rancher" });
    expect(resolveRoute("/rancher/anything")).toEqual({ kind: "rancher" });
  });

  it("preserves /cross-ranch", () => {
    expect(resolveRoute("/cross-ranch")).toEqual({ kind: "cross-ranch" });
  });

  it("parses /attest/:hash and decodes the hash", () => {
    expect(resolveRoute("/attest/abc123")).toEqual({
      kind: "attest",
      hash: "abc123",
    });
    expect(resolveRoute("/attest/ab%3Acd")).toEqual({
      kind: "attest",
      hash: "ab:cd",
    });
  });

  it("falls back to landing for unknown paths", () => {
    expect(resolveRoute("/nonsense")).toEqual({ kind: "landing" });
    expect(resolveRoute("/foo/bar/baz")).toEqual({ kind: "landing" });
  });
});
