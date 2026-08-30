import CountUp from "@/components/CountUp";
import GhostLink from "@/components/GhostLink";
import { scoreCaption, modeLabel } from "@/lib/results";

// Big pixel numeral + the denominator stated in plain sight. The mode
// label is factual -- quality mode is the product, not a degraded run.
export default function ScoreHeader({ analysis, onAddJd }) {
  const isMatch = analysis.mode === "match";
  return (
    <header className="flex flex-col gap-6 border-b border-hairline pb-10 sm:flex-row sm:items-start sm:gap-10">
      <div className="flex shrink-0 items-baseline gap-3">
        <CountUp value={analysis.score} className="font-pixel text-[76px] leading-none text-ink" />
        <span className="font-pixel text-lg text-subtle">/100</span>
      </div>
      <div className="flex flex-col gap-2 pt-1">
        <p className="font-pixel text-sm tracking-[0.14em] text-ink">{modeLabel(analysis)}</p>
        <p className="text-[13px] text-subtle">{scoreCaption(analysis)}</p>
        {!isMatch && (
          <GhostLink onClick={onAddJd} className="mt-1 text-subtle">
            Add a job description to also score role match
            <span aria-hidden className="transition-transform duration-200 ease-stage group-hover:translate-x-0.5">
              →
            </span>
          </GhostLink>
        )}
      </div>
    </header>
  );
}
