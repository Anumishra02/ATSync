import { PageIntro } from "@/components/content/Section";

// The process: four steps, in order, mirroring the labels the progress
// screen shows while a resume is actually running through the pipeline
// (see pages/AnalysisProgressPage.jsx).
const STEPS = [
  {
    n: "01",
    title: "Parse",
    desc: "Your PDF is read three ways at once — the text layer, any hyperlink annotations (an icon-only email or LinkedIn link the text alone would never show), and how that maps onto sections.",
    points: ["Text layer + hyperlink annotations", "Catches icon-only links plain text misses", "Sections identified from real headings"],
  },
  {
    n: "02",
    title: "Score",
    desc: "Six dimensions, each checked against a fixed rubric — not a keyword count. Features has the full breakdown of what each one measures and what it's worth.",
    points: ["Six rubric dimensions, 100 points", "Relevance only runs with a job description", "Each score carries the denominator it used"],
  },
  {
    n: "03",
    title: "Verify",
    desc: "Contact info and links are checked, not estimated: phone validity by region, email deliverability by MX lookup, and whether your links actually resolve.",
    points: ["Phone validity by region", "Email deliverability (MX lookup)", "Link reachability + unclickable-URL detection"],
  },
  {
    n: "04",
    title: "Report",
    desc: "Your score, the points it's actually out of, and — plainly — any dimension it couldn't assess, instead of a silent zero.",
    points: ["Score with its real denominator", "Uncomputable dimensions shown as such", "Verified contact findings, kept separate from the estimates"],
  },
];

export default function HowItWorksPage() {
  return (
    <div className="mx-auto w-full max-w-[720px] px-6 pb-24">
      <PageIntro
        eyebrow="How it works"
        title="What happens when you upload a resume"
        sub="Four steps, in order — the same ones the progress screen shows while it runs."
      />

      <div className="divide-y divide-hairline border-t border-hairline">
        {STEPS.map((s) => (
          <div
            key={s.n}
            className="sd-rise grid grid-cols-[3rem_1fr] gap-x-5 py-8 md:grid-cols-[4rem_1fr] md:gap-x-8"
          >
            <span className="font-pixel text-lg text-subtle">{s.n}</span>
            <div>
              <h3 className="sd-mask font-pixel text-base tracking-wide text-ink">
                <span>{s.title}</span>
              </h3>
              <p className="mt-2 max-w-[480px] text-[13px] leading-relaxed text-subtle">{s.desc}</p>
              <ul className="mt-4 flex flex-col gap-2">
                {s.points.map((p) => (
                  <li key={p} className="grid grid-cols-[0.75rem_1fr] gap-2 text-[13px] text-ink/80">
                    <span className="font-pixel text-flare">·</span>
                    <span>{p}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
