import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

const EASE = [0.22, 1, 0.36, 1];

// Shared building blocks for the content pages (How it works, Features).
// Flat on the stage -- hairline rules, no cards, no chips.

export function PageIntro({ eyebrow, title, sub }) {
  return (
    <motion.header
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7, ease: EASE }}
      className="mx-auto max-w-[720px] px-6 pt-16 pb-10 text-center md:pt-24"
    >
      {eyebrow && (
        <p className="font-pixel text-[11px] uppercase tracking-[0.2em] text-subtle">{eyebrow}</p>
      )}
      <h1 className="mt-4 font-pixel text-[clamp(1.9rem,4.5vw,3rem)] leading-tight text-ink">{title}</h1>
      {sub && <p className="mx-auto mt-4 max-w-[520px] text-[15px] leading-relaxed text-subtle">{sub}</p>}
    </motion.header>
  );
}

export function Section({ id, heading, note, children, className }) {
  return (
    <section id={id} className={cn("border-t border-hairline py-10", className)}>
      {heading && <h2 className="font-pixel text-sm tracking-[0.14em] text-ink">{heading}</h2>}
      {note && <p className="mt-2 max-w-[560px] text-[13px] leading-relaxed text-subtle">{note}</p>}
      <div className={cn(heading && "mt-6")}>{children}</div>
    </section>
  );
}

export function Row({ label, value, sub }) {
  return (
    <div className="grid grid-cols-[1fr_auto] items-baseline gap-x-6 border-b border-hairline py-3 text-[13px] last:border-b-0">
      <div className="min-w-0">
        <span className="text-ink/90">{label}</span>
        {sub && <span className="ml-2 text-absent">{sub}</span>}
      </div>
      {value != null && <span className="font-pixel text-subtle">{value}</span>}
    </div>
  );
}

export function Note({ children }) {
  return (
    <p className="mt-6 border-l-2 border-absent/40 pl-3 text-[13px] leading-relaxed text-subtle">{children}</p>
  );
}
