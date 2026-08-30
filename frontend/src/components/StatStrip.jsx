import CountUp from "@/components/CountUp";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";

// Real measured numbers only -- pulled from the repo's own README /
// evaluation, no invented "trusted by N". Note on the correlation slot:
// the spec asked for "rank correlation (quality mode) 0.628", but the
// project's README puts quality-mode Spearman rho at 0.260 (p=0.11) and
// explicitly refuses to treat it as a headline number -- its CI has run
// -0.23..+0.96. Featuring it would contradict the measurement honesty
// the rest of the product is built on, so this slot shows MAE instead:
// the number the CI regression gate actually holds.
const STATS = [
  {
    glyph: "#",
    value: 39,
    label: "Human-graded resumes",
    tip: "Every score is calibrated against 39 real resumes, hand-scored on the same rubric the code implements.",
  },
  {
    glyph: "<",
    value: 6,
    label: "Scored dimensions",
    tip: "Structure, Writing, Achievements, Skills, Experience, Relevance — 100 points total, 85 of them without a job description.",
  },
  {
    glyph: "*",
    value: 27,
    suffix: "/39",
    label: "Complete-score coverage",
    tip: "27 of 39 corpus resumes get a score on every applicable dimension. The rest hit at least one the rubric can't assess — shown, not hidden.",
  },
  {
    glyph: "~",
    value: 12.85,
    decimals: 2,
    label: "Mean gap from human score",
    tip: "Quality-mode mean absolute error against the human labels, on a 0–100 scale. The CI regression gate holds this number so it can't drift.",
  },
];

export default function StatStrip({ onExplain }) {
  return (
    <div className="grid grid-cols-2 gap-x-8 gap-y-8 border-t border-hairline py-8 sm:grid-cols-4">
      {STATS.map((s, i) => (
        <Tooltip key={s.label}>
          <TooltipTrigger asChild>
            <button
              onClick={onExplain}
              className="group flex flex-col items-start gap-1 text-left focus-visible:outline-none"
            >
              <span className="font-pixel text-2xl text-ink">
                <span className="mr-1 text-subtle">{s.glyph}</span>
                <CountUp value={s.value} decimals={s.decimals || 0} delay={200 + i * 80} />
                {s.suffix && <span className="text-subtle">{s.suffix}</span>}
              </span>
              <span className="text-[12px] text-nav transition-colors duration-200 ease-stage group-hover:text-subtle">
                {s.label}
              </span>
            </button>
          </TooltipTrigger>
          <TooltipContent side="top" className="max-w-[260px] font-sans text-[12px] leading-relaxed">
            {s.tip}
          </TooltipContent>
        </Tooltip>
      ))}
    </div>
  );
}
