import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/sse", () => ({
  getSSE: () => ({ on: vi.fn(), off: vi.fn() }),
}));

describe("audio module", () => {
  beforeEach(() => {
    vi.resetModules();
    localStorage.clear();
  });

  it("exports getAudio", async () => {
    const mod = await import("@/lib/audio");
    expect(typeof mod.getAudio).toBe("function");
  });

  it("returns a singleton", async () => {
    const { getAudio } = await import("@/lib/audio");
    expect(getAudio()).toBe(getAudio());
  });

  it("setMuted is reflected by isMuted", async () => {
    const { getAudio } = await import("@/lib/audio");
    const audio = getAudio();
    audio.setMuted(true);
    expect(audio.isMuted()).toBe(true);
    audio.setMuted(false);
    expect(audio.isMuted()).toBe(false);
  });
});
