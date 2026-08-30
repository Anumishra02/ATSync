// jest-dom adds custom matchers for asserting on DOM nodes
// (e.g. expect(el).toBeInTheDocument()).
import "@testing-library/jest-dom";

// jsdom doesn't implement matchMedia; components that check for
// prefers-reduced-motion rely on it. Default to "no preference".
if (typeof window.matchMedia !== "function") {
  window.matchMedia = (query) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  });
}

// jsdom has neither IntersectionObserver nor ResizeObserver; framer-motion's
// whileInView / layout features need them. Stub as no-ops -- scroll-reveal
// animations aren't under test, the content they wrap is.
class NoopObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords() {
    return [];
  }
}
globalThis.IntersectionObserver ??= NoopObserver;
globalThis.ResizeObserver ??= NoopObserver;
