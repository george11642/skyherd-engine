/**
 * LandingPage composition test — all landing sections render in the expected order.
 * Phase 1 + Phase 5 — TDD RED before implementation.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import LandingPage from "../LandingPage";

describe("LandingPage", () => {
  it("renders every landing section in composition order", () => {
    const { container } = render(<LandingPage />);

    // Scope to the landing root so this test stays hermetic if other
    // sections are ever added outside the landing subtree.
    const root = container.querySelector(".landing-root");
    expect(root).not.toBeNull();

    // Stable markers for each section (by heading text or semantic landmark).
    // Order here matches plan Phase 5.2 exactly.
    const ordered: Array<() => HTMLElement | null> = [
      // Navbar
      () => screen.getByRole("navigation"),
      // Hero — H1 with brand headline
      () => screen.getByRole("heading", { level: 1 }),
      // Problem — H2 "Ranching shouldn't feel like a losing battle"
      () => screen.getByRole("heading", { name: /losing battle/i }),
      // HowItWorks — H2 "How it works"
      () => screen.getByRole("heading", { name: /^how it works$/i }),
      // Capabilities — H2 "Everything your ranch needs in the sky"
      () => screen.getByRole("heading", { name: /everything your ranch needs/i }),
      // Southwest — H2 "We know this land because we're from it"
      () => screen.getByRole("heading", { name: /we know this land/i }),
      // Pricing — H2 "Straightforward. No surprises."
      () => screen.getByRole("heading", { name: /straightforward/i }),
      // FAQ — H2 "Common questions"
      () => screen.getByRole("heading", { name: /common questions/i }),
      // WaitlistForm standalone section — labelled landmark
      () => screen.getByRole("region", { name: /waitlist/i }),
      // Footer
      () => screen.getByRole("contentinfo"),
    ];

    const nodes = ordered.map((getter) => getter());
    nodes.forEach((node) => expect(node).not.toBeNull());

    // Document-order check — each node must appear after the previous one.
    for (let i = 1; i < nodes.length; i++) {
      const prev = nodes[i - 1]!;
      const curr = nodes[i]!;
      const relation = prev.compareDocumentPosition(curr);
      // DOCUMENT_POSITION_FOLLOWING = 4
      expect(relation & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    }
  });

  it("wraps children in .landing-root for token scoping", () => {
    const { container } = render(<LandingPage />);
    expect(container.querySelector(".landing-root")).not.toBeNull();
  });

  it("renders the footer brand-voice line verbatim", () => {
    render(<LandingPage />);
    // Footer copyright with bullet separator (plan line 62).
    expect(
      screen.getByText(/© SkyHerd 2026 · Albuquerque, NM/),
    ).toBeInTheDocument();
  });
});
