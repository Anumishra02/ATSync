import CountUp from "@/components/CountUp";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";

// Real measured numbers only -- pulled from the repo's own README /
// evaluation, no invented "trusted by N", no client logos. The spec's
// original stat 2 ("rank correlation 0.628") isn't in the repo and the
// README explicitly refuses to headline Spearman rho at this sample
// size; an earlier version of this strip showed the quality-mode MAE
// instead, dropped here at the user's request as reading too negative.
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
    glyph: "=",
    value: 3,
    label: "PDF parse channels",
    tip: "Your PDF is read three ways — the text layer, hyperlink annotations, and their merge — so an icon-only email or LinkedIn link isn't missed.",
  },
  {
    glyph: "*",
    value: 27,
    suffix: "/39",
    label: "Fully scored, every dimension",
    tip: "27 of 39 corpus resumes get a score on every applicable dimension. The rest hit at least one the rubric won't guess at — shown, not hidden.",
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
