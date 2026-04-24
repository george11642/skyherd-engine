/**
 * Hero landing section — headline + See Live Demo CTA.
 * Phase 1 + Phase 5 — TDD RED before implementation.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import Hero from "../Hero";

describe("Hero", () => {
  it("renders the exact brand-voice headline", () => {
    render(<Hero />);
    // Headline split across a highlight span — assert the composite text.
    const heading = screen.getByRole("heading", { level: 1 });
    expect(heading.textContent).toBe(
      "Your Ranch Never Sleeps. Neither Does SkyHerd.",
    );
  });

  it("exposes a See Live Demo link pointing at /demo", () => {
    render(<Hero />);
    const link = screen.getByRole("link", { name: /see live demo/i });
    expect(link).toHaveAttribute("href", "/demo");
  });

  it("does not leak placeholder '#' anchors in the hero CTA row", () => {
    render(<Hero />);
    const anchors = screen
      .getAllByRole("link")
      .filter((a) => a.getAttribute("href") === "#");
    expect(anchors).toHaveLength(0);
  });
});
