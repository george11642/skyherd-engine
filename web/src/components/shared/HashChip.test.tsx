/**
 * Tests for the shared HashChip component (Plan 01-01 Task 2).
 * Verifies: hash-chip testid, exactly 4 swatches, full-hash clipboard copy.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, fireEvent, act, waitFor } from "@testing-library/react";
import { HashChip } from "./HashChip";

describe("HashChip", () => {
  beforeEach(() => {
    // jsdom: explicit clipboard stub each test (ensures fresh vi.fn).
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
      writable: true,
      configurable: true,
    });
  });

  it("renders a [data-testid='hash-chip'] element for a memver_ id", async () => {
    await act(async () => {
      render(<HashChip hash="memver_01XRSVdKC1McTbhVbVF5T47E" />);
    });
    const chip = document.querySelector("[data-testid='hash-chip']");
    expect(chip).toBeTruthy();
  });

  it("renders exactly 4 [data-testid='hash-swatch'] elements for a full hex hash", async () => {
    const fullHash = "cafebabedeadbeef12345678aabbccdd99887766554433221100ffeeddccbbaa";
    await act(async () => {
      render(<HashChip hash={fullHash} />);
    });
    const swatches = document.querySelectorAll("[data-testid='hash-swatch']");
    expect(swatches.length).toBe(4);
  });

  it("renders exactly 4 swatches for a non-hex memver_ id (derived via sha256)", async () => {
    await act(async () => {
      render(<HashChip hash="memver_01XRSVdKC1McTbhVbVF5T47E" />);
    });
    // Wait for the async sha256Hex() useEffect to populate derivedHex.
    await waitFor(() => {
      const swatches = document.querySelectorAll("[data-testid='hash-swatch']");
      expect(swatches.length).toBe(4);
    });
  });

  it("clicking the chip writes the FULL hash to navigator.clipboard", async () => {
    const fullHash = "memver_01XRSVdKC1McTbhVbVF5T47E";
    await act(async () => {
      render(<HashChip hash={fullHash} />);
    });
    const chip = document.querySelector("[data-testid='hash-chip']") as HTMLElement;
    expect(chip).toBeTruthy();
    await act(async () => {
      fireEvent.click(chip);
    });
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(fullHash);
  });

  it("degrades gracefully on short hashes", async () => {
    await act(async () => {
      render(<HashChip hash="short" />);
    });
    // Short hashes: render a plain <span>, no hash-chip button at all.
    const chip = document.querySelector("[data-testid='hash-chip']");
    expect(chip).toBeFalsy();
  });
});
