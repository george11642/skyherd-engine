import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/react";
import { TerrainLayer } from "./TerrainLayer";

// Mock ResizeObserver — jsdom doesn't ship one.
class MockResizeObserver {
  observe = vi.fn();
  disconnect = vi.fn();
  unobserve = vi.fn();
}
vi.stubGlobal("ResizeObserver", MockResizeObserver);

interface FakeGLCalls {
  shaderCompiled: number;
  programLinked: boolean;
  useProgramCalls: number;
  drawArraysCalls: Array<[number, number, number]>;
  uniform1fCalls: Array<[unknown, number]>;
  uniform2fCalls: Array<[unknown, number, number]>;
}

function installFakeWebGL2(
  overrides: Partial<{ failShader: boolean; failLink: boolean; failContext: boolean }> = {},
): FakeGLCalls {
  const calls: FakeGLCalls = {
    shaderCompiled: 0,
    programLinked: false,
    useProgramCalls: 0,
    drawArraysCalls: [],
    uniform1fCalls: [],
    uniform2fCalls: [],
  };

  const fakeGl = {
    VERTEX_SHADER: 0x8b31,
    FRAGMENT_SHADER: 0x8b30,
    COMPILE_STATUS: 0x8b81,
    LINK_STATUS: 0x8b82,
    TRIANGLES: 0x0004,
    createShader: () => ({}),
    shaderSource: () => {},
    compileShader: () => {
      calls.shaderCompiled += 1;
    },
    getShaderParameter: () => !overrides.failShader,
    deleteShader: () => {},
    createProgram: () => ({}),
    attachShader: () => {},
    linkProgram: () => {
      if (!overrides.failLink) calls.programLinked = true;
    },
    getProgramParameter: () => !overrides.failLink,
    deleteProgram: () => {},
    createVertexArray: () => ({}),
    bindVertexArray: () => {},
    deleteVertexArray: () => {},
    useProgram: () => {
      calls.useProgramCalls += 1;
    },
    getUniformLocation: () => ({}),
    uniform1f: (loc: unknown, v: number) => {
      calls.uniform1fCalls.push([loc, v]);
    },
    uniform2f: (loc: unknown, x: number, y: number) => {
      calls.uniform2fCalls.push([loc, x, y]);
    },
    uniform3f: () => {},
    drawArrays: (mode: number, first: number, count: number) => {
      calls.drawArraysCalls.push([mode, first, count]);
    },
    viewport: () => {},
  };

  const origGetContext = HTMLCanvasElement.prototype.getContext;
  (HTMLCanvasElement.prototype as unknown as { getContext: unknown }).getContext =
    function (this: HTMLCanvasElement, kind: string) {
      if (kind === "webgl2") {
        return overrides.failContext ? null : (fakeGl as unknown);
      }
      if (kind === "2d") {
        return {
          fillRect: () => {},
          createLinearGradient: () => ({ addColorStop: () => {} }),
          fillStyle: "",
          globalAlpha: 1,
        };
      }
      return (origGetContext as (k: string) => unknown).call(this, kind);
    };

  return calls;
}

function restoreGetContext() {
  // jsdom's default getContext returns null for canvas; restoring via delete
  // to the prototype is cleanest and avoids cross-test leak.
  // @ts-expect-error — test reset
  delete HTMLCanvasElement.prototype.getContext;
}

describe("TerrainLayer", () => {
  let origMatchMedia: typeof window.matchMedia;

  beforeEach(() => {
    origMatchMedia = window.matchMedia;
    // Default: prefers-reduced-motion = false → animation loop runs.
    window.matchMedia = vi.fn().mockImplementation(
      (q: string) =>
        ({
          matches: false,
          media: q,
          addEventListener: () => {},
          removeEventListener: () => {},
          addListener: () => {},
          removeListener: () => {},
          dispatchEvent: () => false,
          onchange: null,
        }) as unknown as MediaQueryList,
    );
  });

  afterEach(() => {
    cleanup();
    restoreGetContext();
    window.matchMedia = origMatchMedia;
  });

  it("renders an aria-hidden canvas", () => {
    installFakeWebGL2();
    const { getByTestId } = render(<TerrainLayer />);
    const canvas = getByTestId("terrain-layer-canvas");
    expect(canvas.getAttribute("aria-hidden")).toBe("true");
    expect(canvas.tagName).toBe("CANVAS");
  });

  it("compiles 2 shaders, links 1 program, and draws a fullscreen triangle", async () => {
    const calls = installFakeWebGL2();
    render(<TerrainLayer />);
    // Give the RAF loop one tick to run.
    await new Promise((r) => setTimeout(r, 50));
    expect(calls.shaderCompiled).toBeGreaterThanOrEqual(2);
    expect(calls.programLinked).toBe(true);
    expect(calls.useProgramCalls).toBeGreaterThanOrEqual(1);
    // drawArrays(TRIANGLES, 0, 3) — fullscreen-triangle trick
    const triangleDraw = calls.drawArraysCalls.find(
      ([, first, count]) => first === 0 && count === 3,
    );
    expect(triangleDraw).toBeDefined();
  });

  it("falls back gracefully when WebGL2 context is unavailable", () => {
    installFakeWebGL2({ failContext: true });
    // Must not throw.
    const { getByTestId } = render(<TerrainLayer />);
    expect(getByTestId("terrain-layer-canvas")).toBeTruthy();
  });

  it("falls back when shader compilation fails", () => {
    const calls = installFakeWebGL2({ failShader: true });
    render(<TerrainLayer />);
    // Must not attempt to link or draw.
    expect(calls.programLinked).toBe(false);
    expect(calls.drawArraysCalls.length).toBe(0);
  });

  it("respects prefers-reduced-motion: reduce by pinning uTime to 0", async () => {
    // Override matchMedia to match reduced-motion.
    window.matchMedia = vi.fn().mockImplementation(
      (q: string) =>
        ({
          matches: q.includes("prefers-reduced-motion"),
          media: q,
          addEventListener: () => {},
          removeEventListener: () => {},
          addListener: () => {},
          removeListener: () => {},
          dispatchEvent: () => false,
          onchange: null,
        }) as unknown as MediaQueryList,
    );
    const calls = installFakeWebGL2();
    render(<TerrainLayer />);
    // Wait a bit to ensure multiple frames would have elapsed without the guard.
    await new Promise((r) => setTimeout(r, 120));
    // Every uniform1f call for uTime must be 0 (static render).
    const timeValues = calls.uniform1fCalls.map(([, v]) => v);
    expect(timeValues.length).toBeGreaterThanOrEqual(1);
    for (const v of timeValues) {
      expect(v).toBe(0);
    }
  });
});
