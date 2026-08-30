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
