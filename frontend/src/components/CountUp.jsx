import { useEffect, useRef, useState } from "react";

const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);

const prefersReducedMotion = () =>
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/**
 * Count-up numeral. easeOutCubic, ~1500ms by default. Snaps straight to
 * the value under prefers-reduced-motion. `delay` staggers a row of them.
 */
export default function CountUp({ value, duration = 1500, delay = 0, decimals = 0, className }) {
  const [display, setDisplay] = useState(prefersReducedMotion() ? value : 0);
  const frame = useRef();

  useEffect(() => {
    if (prefersReducedMotion()) {
      setDisplay(value);
      return;
    }
    let startTs;
    let timeoutId;
    const tick = (ts) => {
      if (startTs === undefined) startTs = ts;
      const elapsed = ts - startTs;
      const t = Math.min(1, elapsed / duration);
      setDisplay(value * easeOutCubic(t));
      if (t < 1) frame.current = requestAnimationFrame(tick);
      else setDisplay(value);
    };
    timeoutId = setTimeout(() => {
      frame.current = requestAnimationFrame(tick);
    }, delay);
    return () => {
      clearTimeout(timeoutId);
      cancelAnimationFrame(frame.current);
    };
  }, [value, duration, delay]);

  return <span className={className}>{display.toFixed(decimals)}</span>;
}
