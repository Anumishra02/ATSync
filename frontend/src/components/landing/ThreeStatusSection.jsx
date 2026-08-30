import ScrollReveal from "@/components/landing/ScrollReveal";
import { cn } from "@/lib/utils";

const STATES = [
  {
    tag: "scored",
    tone: "text-flare",
    dim: "Structure",
    value: "15 / 15",
    note: "A real number was computed. Every section a resume needs was present and correctly headed.",
  },
  {
    tag: "uncomputable",
    tone: "text-absent",
    dim: "Achievements",
    value: "— / 20",
    note: "No bulleted content, so quantified impact can't be assessed. Not the same as scoring zero — and not hidden.",
  },
  {
    tag: "not applicable",
    tone: "text-absent",
    dim: "Relevance",
    value: "— / 15",
    note: "This dimension only runs with a job description. Its points aren't counted against you — the denominator drops instead.",
  },
];

// The differentiator, up front: a missing sub-score has three different
// causes and collapsing them into 0 destroys the distinction.
export default function ThreeStatusSection() {
  return (
    <section className="border-t border-hairline py-24">
      <div className="mx-auto max-w-[1000px] px-6 md:px-12">
        <ScrollReveal scrub>
          <p className="font-pixel text-[11px] uppercase tracking-[0.2em] text-subtle">The three-status model</p>
          <h2 className="sd-mask mt-4 max-w-[620px] font-pixel text-[clamp(1.6rem,3vw,2.2rem)] leading-tight text-ink">
            <span>A score it couldn&rsquo;t compute is never a zero</span>
          </h2>
          <p className="mt-4 max-w-[500px] text-[15px] leading-relaxed text-subtle">
            Every dimension reports one of three states. &ldquo;Didn&rsquo;t apply&rdquo; and &ldquo;couldn&rsquo;t
            be read&rdquo; look nothing like &ldquo;read it, found nothing&rdquo; — so they aren&rsquo;t drawn that
            way.
          </p>
        </ScrollReveal>

        <div className="mt-12 grid gap-4 md:grid-cols-3">
          {STATES.map((s, i) => (
            <ScrollReveal
              key={s.tag}
              delay={0.12 * i}
              className="card-bloom group relative rounded-xl border border-white/[0.06] bg-card/70 p-5 transition duration-300 ease-stage hover:-translate-y-1.5 hover:scale-[1.03] hover:border-white/25 hover:brightness-105 hover:shadow-[0_30px_80px_-20px_rgba(0,0,0,0.85)]"
            >
              <span
                aria-hidden
                className="pointer-events-none absolute right-3 top-3 grid h-6 w-6 place-items-center rounded-md border border-white/15 text-[12px] text-ink opacity-0 transition-opacity duration-300 ease-stage group-hover:opacity-100"
              >
                ↗
              </span>
              <div className="flex items-baseline justify-between">
                <span className="text-[13px] font-medium text-ink">{s.dim}</span>
                <span className={cn("font-pixel text-sm", s.tone)}>{s.value}</span>
              </div>
              <p className={cn("mt-3 font-pixel text-[10px] uppercase tracking-wider", s.tone)}>{s.tag}</p>
              <p className="mt-2 text-[12px] leading-relaxed text-subtle">{s.note}</p>
            </ScrollReveal>
          ))}
        </div>
      </div>
    </section>
  );
}
