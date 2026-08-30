import { motion, useScroll, useTransform } from "framer-motion";
import { TooltipProvider } from "@/components/ui/tooltip";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import FluidCanvas from "@/components/FluidCanvas";

// App frame: tooltip context + fixed header + a main region that clears
// it. The fluid canvas and a scroll-driven veil now live here so every
// page sits over the same moving backdrop -- the veil starts as a light
// translucent black and darkens toward solid as you scroll, so reading
// pages stay legible while the hero stays clean.
//
// `showFooter` is off for the landing viewport. `bare` means the landing
// hero: the veil starts fully transparent. Every other page starts only
// lightly dimmed -- the fluid should read at full strength everywhere --
// and the veil deepens toward near-solid as you scroll into the reading
// content.
export default function Shell({
  page,
  onNavigate,
  onHome,
  onCheckResume,
  showFooter = true,
  bare = false,
  children,
}) {
  const { scrollY } = useScroll();
  const veil = useTransform(scrollY, [0, 620], [bare ? 0 : 0.14, 0.9]);

  return (
    <TooltipProvider delayDuration={150}>
      <div className="relative flex min-h-screen flex-col text-ink">
        <FluidCanvas />
        <motion.div
          aria-hidden
          style={{ opacity: veil }}
          className="pointer-events-none fixed inset-0 z-0 bg-[#050505]"
        />

        <Header page={page} onNavigate={onNavigate} onHome={onHome} onCheckResume={onCheckResume} />
        <main className="relative z-10 flex flex-1 flex-col pt-[60px]">{children}</main>
        {showFooter && (
          <div className="relative z-10">
            <Footer onNavigate={onNavigate} />
          </div>
        )}
      </div>
    </TooltipProvider>
  );
}
