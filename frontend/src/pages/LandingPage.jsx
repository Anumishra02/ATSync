import { motion } from "framer-motion";
import FluidCanvas from "@/components/FluidCanvas";
import StatStrip from "@/components/StatStrip";
import Pill from "@/components/Pill";
import GhostLink from "@/components/GhostLink";

const EASE = [0.22, 1, 0.36, 1];
const rise = (delay) => ({
  initial: { opacity: 0, y: 14 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.85, delay, ease: EASE },
});

// Spec Page 1. Single viewport: header (Shell) / hero / stat strip. The
// fluid canvas is fixed behind everything and lives only here.
export default function LandingPage({ onCheckResume, onHowItWorks, onExplainMetrics }) {
  return (
    <div className="relative flex flex-1 flex-col">
      <FluidCanvas />

      <div className="relative z-10 mx-auto flex w-full max-w-[1000px] flex-1 flex-col px-6 md:px-12">
        <div className="flex flex-1 flex-col justify-center py-16">
          <motion.h1 {...rise(0.12)} className="font-pixel text-[clamp(2.5rem,7vw,5rem)] leading-[1.05] text-ink">
            ATSync
            <span className="mt-1 block text-[clamp(1.5rem,3.4vw,2.5rem)] leading-tight text-ink">
              Resume analysis that admits what it can&rsquo;t measure
            </span>
          </motion.h1>

          <motion.p {...rise(0.28)} className="mt-6 max-w-[500px] text-[15px] leading-relaxed text-subtle">
            Six scored dimensions against a human-graded rubric. Verified contact and link checks. Every score
            reports the denominator it was computed from.
          </motion.p>

          <motion.div {...rise(0.4)} className="mt-9 flex items-center gap-6">
            <Pill size="lg" onClick={onCheckResume}>
              Check Resume
            </Pill>
            <GhostLink onClick={onHowItWorks}>
              How it works
              <span aria-hidden className="transition-transform duration-200 ease-stage group-hover:translate-x-0.5">
                →
              </span>
            </GhostLink>
          </motion.div>
        </div>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.6, delay: 0.5 }}>
          <StatStrip onExplain={onExplainMetrics} />
        </motion.div>
      </div>
    </div>
  );
}
