import "@testing-library/jest-dom";

// jsdom has no IntersectionObserver; framer-motion's `whileInView`
// crashes without it. Stub it so landing-page tests (and any other
// consumer of motion's viewport features) can mount cleanly.
if (typeof globalThis.IntersectionObserver === "undefined") {
  class IntersectionObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
    takeRecords() {
      return [];
    }
    root: Element | null = null;
    rootMargin = "";
    thresholds: ReadonlyArray<number> = [];
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (globalThis as any).IntersectionObserver = IntersectionObserverStub;
}

// jsdom HTMLCanvasElement returns null from getContext("2d") and emits
// "Not implemented" errors that crash any component painting to canvas
// (TerrainLayer, RanchMap predator rings, etc.). Provide a no-op 2D
// context so component tests can mount. Tests that need to assert on
// canvas behavior (e.g. RanchMap's predator pulse alpha) install their
// own richer mock and override this default.
if (typeof HTMLCanvasElement !== "undefined") {
  const noop = () => {};
  const fakeContext: Record<string, unknown> = {
    canvas: null,
    fillStyle: "#000",
    strokeStyle: "#000",
    globalAlpha: 1,
    lineWidth: 1,
    font: "10px sans-serif",
    textAlign: "left",
    save: noop,
    restore: noop,
    scale: noop,
    translate: noop,
    rotate: noop,
    beginPath: noop,
    closePath: noop,
    moveTo: noop,
    lineTo: noop,
    arc: noop,
    ellipse: noop,
    rect: noop,
    roundRect: noop,
    fill: noop,
    stroke: noop,
    fillRect: noop,
    strokeRect: noop,
    clearRect: noop,
    fillText: noop,
    strokeText: noop,
    setLineDash: noop,
    getLineDash: () => [],
    drawImage: noop,
    createLinearGradient: () => ({ addColorStop: noop }),
    createRadialGradient: () => ({ addColorStop: noop }),
    createPattern: () => null,
    measureText: () => ({ width: 0 }),
    getImageData: () => ({ data: new Uint8ClampedArray(4), width: 1, height: 1 }),
    putImageData: noop,
  };
  const origGetContext = HTMLCanvasElement.prototype.getContext;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (HTMLCanvasElement.prototype as any).getContext = function (
    this: HTMLCanvasElement,
    kind: string,
  ) {
    if (kind === "2d") {
      // return a fresh shallow clone so per-canvas property mutations don't leak
      return { ...fakeContext, canvas: this };
    }
    // Defer to original (returns null in jsdom for unsupported contexts)
    return origGetContext?.call(this, kind) ?? null;
  };
}

// jsdom has no AudioContext; the dashboard audio cue module instantiates
// one on first user interaction. Provide a no-op stub so component tests
// that import `@/lib/audio` (transitively via SSE wiring) don't blow up
// with "AudioContext is not defined".
if (typeof (globalThis as unknown as { AudioContext?: unknown }).AudioContext === "undefined") {
  class FakeOscillator {
    type = "sine";
    frequency = { setValueAtTime: () => {}, exponentialRampToValueAtTime: () => {} };
    connect() {}
    disconnect() {}
    start() {}
    stop() {}
  }
  class FakeGain {
    gain = {
      value: 0,
      setValueAtTime: () => {},
      linearRampToValueAtTime: () => {},
      exponentialRampToValueAtTime: () => {},
    };
    connect() {}
    disconnect() {}
  }
  class FakeAudioContext {
    state = "running";
    currentTime = 0;
    destination = {};
    createOscillator() {
      return new FakeOscillator();
    }
    createGain() {
      return new FakeGain();
    }
    resume() {
      return Promise.resolve();
    }
    suspend() {
      return Promise.resolve();
    }
    close() {
      return Promise.resolve();
    }
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (globalThis as any).AudioContext = FakeAudioContext;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (globalThis as any).webkitAudioContext = FakeAudioContext;
}
