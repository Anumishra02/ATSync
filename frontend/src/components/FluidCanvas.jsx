import { Suspense, lazy, useEffect, useState } from "react";

// Vendored WebGL sim (~1100 lines of shader code) -- only ever mounts on
// the landing page, and only when motion is allowed on a wide-enough
// viewport, so keep it out of the initial bundle.
const FluidCursor = lazy(() => import("@/vendor/FluidCursor"));

const MOBILE_MAX = 768;

function hasWebGL() {
  try {
    const c = document.createElement("canvas");
    return !!(c.getContext("webgl2") || c.getContext("webgl") || c.getContext("experimental-webgl"));
  } catch {
    return false;
  }
}

// Warm plumes on a near-black stage, high dissipation. Landing page only.
// Off entirely under prefers-reduced-motion, off below 768px (battery,
// and touch has no hover), and unmounted while the tab is hidden so the
// GL loop isn't running against a background tab.
export default function FluidCanvas() {
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    if (typeof window.matchMedia !== "function" || !hasWebGL()) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    const compute = () => !reduced.matches && window.innerWidth >= MOBILE_MAX && !document.hidden;

    const update = () => setEnabled(compute());
    update();

    window.addEventListener("resize", update);
    document.addEventListener("visibilitychange", update);
    reduced.addEventListener?.("change", update);
    return () => {
      window.removeEventListener("resize", update);
      document.removeEventListener("visibilitychange", update);
      reduced.removeEventListener?.("change", update);
    };
  }, []);

  if (!enabled) return null;

  return (
    <Suspense fallback={null}>
      <FluidCursor
        RAINBOW_MODE={false}
        COLOR="#d9974a"
        BACK_COLOR={{ r: 0.02, g: 0.02, b: 0.02 }}
        TRANSPARENT
        DENSITY_DISSIPATION={4.6}
        VELOCITY_DISSIPATION={2.6}
        SPLAT_RADIUS={0.16}
        SPLAT_FORCE={5200}
        CURL={2.4}
        COLOR_UPDATE_SPEED={0}
        SHADING
      />
    </Suspense>
  );
}
