import ScrollReveal from "@/components/landing/ScrollReveal";
import Pill from "@/components/Pill";

export default function ClosingCTA({ onCheckResume }) {
  return (
    <section className="border-t border-hairline py-28">
      <ScrollReveal className="mx-auto max-w-[1000px] px-6 text-center md:px-12">
        <h2 className="mx-auto max-w-[560px] font-pixel text-[clamp(1.8rem,3.4vw,2.6rem)] leading-tight text-ink">
          See what it can — and can&rsquo;t — tell you about your resume
        </h2>
        <div className="mt-8 flex justify-center">
          <Pill size="lg" onClick={onCheckResume}>
            Check Resume
          </Pill>
        </div>
        <p className="mt-4 text-[12px] text-absent">One PDF · processed in memory, not stored</p>
      </ScrollReveal>
    </section>
  );
}
