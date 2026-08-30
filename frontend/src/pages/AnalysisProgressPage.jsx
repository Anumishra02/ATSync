import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

const ANALYZE_STAGES = [
  "PARSING PDF",
  "EXTRACTING SECTIONS",
  "MATCHING SKILLS",
  "SCORING DIMENSIONS",
  "VERIFYING CONTACTS & LINKS",
];

const CELLS = 10;

function Bar({ state }) {
  // done -> full, active -> ~6 cells with a pulse, pending -> empty.
  const filled = state === "done" ? CELLS : state === "active" ? 6 : 0;
  return (
    <span className="inline-flex gap-px" aria-hidden>
      {Array.from({ length: CELLS }, (_, i) => (
        <span
          key={i}
          className={cn(
            "h-2.5 w-2 rounded-[1px]",
            i < filled ? (state === "done" ? "bg-ok" : "bg-ok/70") : "bg-hairline",
            state === "active" && i < filled && "motion-safe:animate-pulse",
          )}
        />
      ))}
    </span>
  );
}

function Row({ label, state, index }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: state === "pending" ? 0.35 : 1 }}
      transition={{ duration: 0.4, delay: index * 0.06, ease: [0.22, 1, 0.36, 1] }}
      className="grid grid-cols-[1.2rem_minmax(0,1fr)_auto_3.5rem] items-center gap-3 font-pixel text-[13px]"
    >
      <span className={state === "done" ? "text-ok" : "text-subtle"}>{state === "done" ? "✓" : ">"}</span>
      <span className={cn("truncate uppercase tracking-wider", state === "done" ? "text-ok" : "text-ink")}>
        {label}
      </span>
      <Bar state={state} />
      <span className={cn("text-right text-[11px]", state === "done" ? "text-ok" : "text-absent")}>
        {state === "done" ? "done" : state === "active" ? "…" : ""}
      </span>
    </motion.div>
  );
}

// Spec Page 4 -- the dot-matrix moment. Real backend stages, revealed
// sequentially, completed rows stay. `stage` is how many are done (0..N);
// `coldStart` appends the honest Render-spin-down line after 8s of no
// response. `variant="cover-letter"` is the single-row, up-to-60s form.
export default function AnalysisProgressPage({ stage = 0, coldStart = false, variant = "analyze" }) {
  const stages = variant === "cover-letter" ? ["GENERATING COVER LETTER"] : ANALYZE_STAGES;
  const visibleCount = variant === "cover-letter" ? 1 : Math.min(stages.length, stage + 1);
  const [dots, setDots] = useState("");

  useEffect(() => {
    const id = setInterval(() => setDots((d) => (d.length >= 3 ? "" : d + ".")), 400);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="mx-auto flex w-full max-w-[560px] flex-1 flex-col justify-center px-6 py-16">
      <p className="font-pixel text-sm tracking-[0.14em] text-subtle">
        {variant === "cover-letter" ? "WRITING" : "ANALYSING"}
        <span className="text-absent">{dots}</span>
      </p>

      <div className="mt-6 flex flex-col gap-3">
        {stages.slice(0, visibleCount).map((label, i) => {
          const state = i < stage ? "done" : i === stage ? "active" : "pending";
          return <Row key={label} label={label} state={variant === "cover-letter" ? "active" : state} index={i} />;
        })}
      </div>

      {coldStart && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mt-6 border-l-2 border-absent/40 pl-3 text-[12px] text-absent"
        >
          Server was idle — the first request can take up to a minute. This is the free tier spinning back up,
          not a hang.
        </motion.p>
      )}
    </div>
  );
}
