import { motion } from "framer-motion";
import ScoreHeader from "@/components/results/ScoreHeader";
import DimensionRow from "@/components/results/DimensionRow";
import ContactLinks from "@/components/results/ContactLinks";
import GhostLink from "@/components/GhostLink";
import { DIMENSIONS } from "@/lib/constants";

const EASE = [0.22, 1, 0.36, 1];

// The primary screen. Three regions: score header, six dimensions, and
// Contact & Links. No dimension is ever rendered as 0 or hidden -- an
// absent score is itself the finding.
export default function ResultsPage({ analysis, onReset, onAddJd }) {
  const byKey = Object.fromEntries(analysis.dimensions.map((d) => [d.dimension, d]));
  const ordered = DIMENSIONS.map((meta) => byKey[meta.key]).filter(Boolean);

  return (
    <div className="mx-auto w-full max-w-[760px] px-6 py-14 md:py-20">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: EASE }}
      >
        <ScoreHeader analysis={analysis} onAddJd={onAddJd} />

        <div className="mt-4 divide-y divide-hairline">
          {ordered.map((dim, i) => (
            <div
              key={dim.dimension}
              className="sd-rise"
              style={{ animationRange: `entry ${2 + i * 4}% cover ${28 + i * 3}%` }}
            >
              <DimensionRow dim={dim} />
            </div>
          ))}
        </div>

        <div className="sd-rise mt-10">
          <ContactLinks contact={analysis.contact_links} parse={analysis.parse} />
        </div>

        <div className="mt-12 flex items-center gap-6 border-t border-hairline pt-8">
          <GhostLink onClick={onReset}>
            <span aria-hidden>←</span> Analyse another resume
          </GhostLink>
        </div>
      </motion.div>
    </div>
  );
}
