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
