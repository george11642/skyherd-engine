import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, act, fireEvent } from "@testing-library/react";
import { VetIntakePanel, renderMarkdown, parsePixelDetections } from "./VetIntakePanel";

// SSE mock — shared handlers registry so tests can fire events
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

describe("VetIntakePanel (SCEN-01 UI)", () => {
  beforeEach(() => {
    sseHandlers = {};
    vi.clearAllMocks();
  });

  it("renders a title initially (empty state OK)", async () => {
    await act(async () => {
      render(<VetIntakePanel />);
    });
    // Title is a fixed string; empty-state text differs. Use the exact label.
    expect(screen.getByText("Vet Intake")).toBeTruthy();
    // And the empty state placeholder.
    expect(screen.getByText(/no vet intakes yet/i)).toBeTruthy();
  });

  it("fetches and renders markdown after vet_intake.drafted SSE event", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        text: () =>
          Promise.resolve(
            "# Vet Intake — A014 · Pinkeye · ESCALATE\n\n## Cow\n- Tag: A014\n\n## Finding\n- Disease: Pinkeye\n",
          ),
        headers: new Headers({ "content-type": "text/markdown" }),
      }),
    );

    const { container } = await act(async () => {
      return render(<VetIntakePanel />);
    });

    await act(async () => {
      triggerSSE("vet_intake.drafted", {
        id: "A014_20260101T000000Z",
        cow_tag: "A014",
        severity: "escalate",
        disease: "pinkeye",
        path: "runtime/vet_intake/A014_20260101T000000Z.md",
        ts: 1760000000,
      });
    });

    await waitFor(() => expect(container.textContent).toMatch(/A014/i));
  });

  it("inline markdown renderer converts ## headings and **bold**", () => {
    const html = renderMarkdown("## Cow\n**bold** normal");
    expect(html).toContain("<h3>Cow</h3>");
    expect(html).toContain("<strong>bold</strong>");
  });

  it("severity chip maps escalate->danger, observe->warn, log->muted", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        text: () => Promise.resolve("# Vet Intake — A014\n"),
        headers: new Headers({ "content-type": "text/markdown" }),
      }),
    );

    await act(async () => {
      render(<VetIntakePanel />);
    });

    await act(async () => {
      triggerSSE("vet_intake.drafted", {
        id: "A014_20260101T000000Z",
        cow_tag: "A014",
        severity: "escalate",
        disease: "pinkeye",
        path: "runtime/vet_intake/A014_20260101T000000Z.md",
        ts: 1760000000,
      });
    });
    await act(async () => {
      triggerSSE("vet_intake.drafted", {
        id: "B022_20260101T000000Z",
        cow_tag: "B022",
        severity: "observe",
        disease: "brd",
        path: "runtime/vet_intake/B022_20260101T000000Z.md",
        ts: 1760000100,
      });
    });
    await act(async () => {
      triggerSSE("vet_intake.drafted", {
        id: "C033_20260101T000000Z",
        cow_tag: "C033",
        severity: "log",
        disease: "foot_rot",
        path: "runtime/vet_intake/C033_20260101T000000Z.md",
        ts: 1760000200,
      });
    });

    // Severity chips should render with class indicators
    await waitFor(() => {
      expect(screen.getByText(/A014/i)).toBeTruthy();
      expect(screen.getByText(/B022/i)).toBeTruthy();
      expect(screen.getByText(/C033/i)).toBeTruthy();
    });

    // Each row has a chip with class matching the severity mapping
    const escChip = screen.getByTestId(`severity-chip-A014_20260101T000000Z`);
    expect(escChip.className).toMatch(/chip-danger/);
    const obsChip = screen.getByTestId(`severity-chip-B022_20260101T000000Z`);
    expect(obsChip.className).toMatch(/chip-warn/);
    const logChip = screen.getByTestId(`severity-chip-C033_20260101T000000Z`);
    expect(logChip.className).toMatch(/chip-muted/);
  });
});

describe("VetIntakePanel — DASH-06 pixel-detection chip", () => {
  beforeEach(() => {
    sseHandlers = {};
    vi.clearAllMocks();
  });

  it("parsePixelDetections extracts kind/head/bbox/conf from markdown body", () => {
    const md = [
      "# Vet Intake — A014 · Pinkeye · ESCALATE",
      "",
      "## Structured Signals (DASH-06)",
      "- kind=pixel_detection head=pinkeye bbox=[321, 120, 412, 198] conf=0.87",
      "- kind=pixel_detection head=screwworm bbox=[10, 20, 30, 40] conf=0.55",
      "",
    ].join("\n");
    const dets = parsePixelDetections(md);
    expect(dets).toHaveLength(2);
    expect(dets[0]).toEqual({
      head: "pinkeye",
      bbox: [321, 120, 412, 198],
      confidence: 0.87,
    });
    expect(dets[1].head).toBe("screwworm");
    expect(dets[1].bbox).toEqual([10, 20, 30, 40]);
    expect(dets[1].confidence).toBeCloseTo(0.55, 2);
  });

  it("renders a pixel-detection chip when structured signals are present", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        text: () =>
          Promise.resolve(
            [
              "# Vet Intake — A014 · Pinkeye · ESCALATE",
              "",
              "## Cow",
              "- Tag: A014",
              "",
              "## Structured Signals (DASH-06)",
              "- kind=pixel_detection head=pinkeye bbox=[321, 120, 412, 198] conf=0.87",
            ].join("\n"),
          ),
        headers: new Headers({ "content-type": "text/markdown" }),
      }),
    );

    await act(async () => {
      render(<VetIntakePanel />);
    });
    await act(async () => {
      triggerSSE("vet_intake.drafted", {
        id: "A014_20260101T000000Z",
        cow_tag: "A014",
        severity: "escalate",
        disease: "pinkeye",
        path: "runtime/vet_intake/A014_20260101T000000Z.md",
        ts: 1760000000,
      });
    });

    // Click the intake row to open the detail with the chip
    await waitFor(() => expect(screen.getByText(/A014/i)).toBeTruthy());
    const row = screen.getByText(/A014/i);
    await act(async () => {
      fireEvent.click(row);
    });

    const chip = await screen.findByTestId("pixel-detection-chip");
    expect(chip).toBeTruthy();
    expect(chip.textContent).toMatch(/pinkeye/i);
    expect(chip.textContent).toMatch(/321/);
    expect(chip.textContent).toMatch(/(0\.87|87%)/);
  });

  it("renders NO pixel-detection chip when structured signals are absent", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        text: () =>
          Promise.resolve(
            "# Vet Intake — B022 · Pinkeye · OBSERVE\n\n## Cow\n- Tag: B022\n",
          ),
        headers: new Headers({ "content-type": "text/markdown" }),
      }),
    );

    await act(async () => {
      render(<VetIntakePanel />);
    });
    await act(async () => {
      triggerSSE("vet_intake.drafted", {
        id: "B022_20260101T000000Z",
        cow_tag: "B022",
        severity: "observe",
        disease: "pinkeye",
        path: "runtime/vet_intake/B022_20260101T000000Z.md",
        ts: 1760000100,
      });
    });

    await waitFor(() => expect(screen.getByText(/B022/i)).toBeTruthy());
    await act(async () => {
      fireEvent.click(screen.getByText(/B022/i));
    });
    expect(screen.queryByTestId("pixel-detection-chip")).toBeNull();
  });
});
