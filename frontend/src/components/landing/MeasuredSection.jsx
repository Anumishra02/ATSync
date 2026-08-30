import ScrollReveal from "@/components/landing/ScrollReveal";
import GhostLink from "@/components/GhostLink";

const FACTS = [
  {
    k: "39",
    t: "A frozen, human-labelled corpus",
    d: "39 real resumes, each scored by hand on the same rubric the code implements. The labels don't move once set — scorers are measured against them, not tuned to them.",
  },
  {
    k: "2",
    t: "Coverage reported next to accuracy",
    d: "How often a dimension can run is shown separately from how close it lands — a wide-coverage/low-accuracy tool and a narrow one fail differently and look identical if you only report one number.",
  },
  {
    k: "CI",
    t: "A regression gate on every push",
    d: "Coverage and mean signed gap are contracts, checked in CI. Spearman rank correlation deliberately isn't — at this sample size its confidence interval has run from −0.23 to +0.96, too unstable to gate on.",
  },
  {
    k: "1",
    t: "A component that was cut, on the record",
    d: "An embedding-cosine skill matcher was built, measured against a bar set before the numbers existed, and removed when recall never cleared ~0.46. Kept in the write-up as evidence of the discipline.",
  },
];

// Real measurement facts, pulled from the repo's README and evaluation
// notes. No praise, no invented proof -- the honesty is the pitch.
export default function MeasuredSection({ onMore }) {
  return (
    <section className="border-t border-hairline py-24">
      <div className="mx-auto max-w-[1000px] px-6 md:px-12">
        <ScrollReveal>
          <p className="font-pixel text-[11px] uppercase tracking-[0.2em] text-subtle">How it was measured</p>
          <h2 className="mt-4 max-w-[620px] font-pixel text-[clamp(1.6rem,3vw,2.2rem)] leading-tight text-ink">
            The part most resume tools don&rsquo;t show
          </h2>
        </ScrollReveal>

        <div className="mt-12 grid gap-x-10 gap-y-8 sm:grid-cols-2">
          {FACTS.map((f, i) => (
            <ScrollReveal key={f.t} delay={0.06 * i} className="grid grid-cols-[3rem_1fr] gap-4">
              <span className="font-pixel text-lg text-subtle">{f.k}</span>
              <div>
                <h3 className="text-[14px] font-medium text-ink">{f.t}</h3>
                <p className="mt-1.5 text-[13px] leading-relaxed text-subtle">{f.d}</p>
              </div>
            </ScrollReveal>
          ))}
        </div>

        <ScrollReveal delay={0.1} className="mt-10">
          <GhostLink onClick={onMore}>
            The full breakdown
            <span aria-hidden className="transition-transform duration-200 ease-stage group-hover:translate-x-0.5">
              →
            </span>
          </GhostLink>
        </ScrollReveal>
      </div>
    </section>
  );
}
