import { useRef } from "react";
import { motion, useScroll, useTransform, useSpring, useMotionValue } from "framer-motion";
import ScrollReveal from "@/components/landing/ScrollReveal";

const PLANES = [
  {
    key: "text",
    title: "Text layer",
    body: "Every character the PDF actually contains, in reading order — column-aware, so a two-column resume doesn't scramble.",
    baseZ: 80,
    lines: ["ANU MISHRA", "EXPERIENCE", "Built REST APIs · 30% faster", "SKILLS  Python · React · FastAPI"],
  },
  {
    key: "annotations",
    title: "Link annotations",
    body: "The hyperlink targets embedded in the file — an icon-only mailto: or a LinkedIn link with no visible URL a text-only parser never sees.",
    baseZ: 40,
    lines: ["→ mailto:anu@example.com", "→ linkedin.com/in/anumish", "→ github.com/Anumishra02"],
  },
  {
    key: "merged",
    title: "Merged",
    body: "The two channels reconciled into one — what the scorers and the contact checks actually run against.",
    baseZ: 0,
    lines: ["ANU MISHRA · anu@example.com", "linkedin.com/in/anumish (found)", "EXPERIENCE · SKILLS · EDUCATION"],
  },
];

function Plane({ plane, spread }) {
  const z = useTransform(spread, (s) => plane.baseZ * s);
  return (
    <motion.div
      style={{ translateZ: z, transformStyle: "preserve-3d" }}
      className="card-bloom absolute inset-0 rounded-xl border border-hairline bg-card/85 p-5 shadow-[0_24px_70px_-24px_rgba(0,0,0,0.85)] backdrop-blur-sm"
    >
      <p className="font-pixel text-[11px] uppercase tracking-wider text-subtle">{plane.title}</p>
      <div className="mt-3 flex flex-col gap-1.5">
        {plane.lines.map((l, i) => (
          <p key={i} className="truncate font-pixel text-[11px] text-ink/70">
            {l}
          </p>
        ))}
      </div>
    </motion.div>
  );
}

// The three-channel parser as an interactive 3D stack. Scroll pulls the
// planes apart through the middle of the section and lets them settle
// back together; the cursor tilts the whole stack.
export default function ParseChannelsSection() {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end start"] });

  const spread = useSpring(useTransform(scrollYProgress, [0, 0.5, 1], [0.3, 1, 0.3]), {
    stiffness: 70,
    damping: 20,
  });
  const scrollRotX = useTransform(scrollYProgress, [0, 1], [24, 6]);

  const pointerX = useMotionValue(0); // -0.5 .. 0.5
  const pointerY = useMotionValue(0);
  const rotX = useSpring(useTransform([scrollRotX, pointerY], ([r, py]) => r + -py * 10), {
    stiffness: 120,
    damping: 18,
  });
  const rotY = useSpring(useTransform(pointerX, (px) => px * 18), { stiffness: 120, damping: 18 });

  const onMove = (e) => {
    const r = e.currentTarget.getBoundingClientRect();
    pointerX.set((e.clientX - r.left) / r.width - 0.5);
    pointerY.set((e.clientY - r.top) / r.height - 0.5);
  };
  const reset = () => {
    pointerX.set(0);
    pointerY.set(0);
  };

  return (
    <section ref={ref} className="border-t border-hairline py-24">
      <div className="mx-auto grid max-w-[1000px] gap-12 px-6 md:grid-cols-2 md:items-center md:px-12">
        <div>
          <ScrollReveal scrub>
            <p className="font-pixel text-[11px] uppercase tracking-[0.2em] text-subtle">Parse</p>
            <h2 className="sd-mask mt-4 font-pixel text-[clamp(1.6rem,3vw,2.2rem)] leading-tight text-ink">
              <span>Three reads of one PDF</span>
            </h2>
          </ScrollReveal>
          <div className="mt-6 flex flex-col gap-5">
            {PLANES.map((p, i) => (
              <ScrollReveal key={p.key} delay={0.08 * i}>
                <p className="text-[13px] font-medium text-ink">{p.title}</p>
                <p className="mt-1 max-w-[420px] text-[13px] leading-relaxed text-subtle">{p.body}</p>
              </ScrollReveal>
            ))}
          </div>
        </div>

        <div
          className="relative mx-auto h-[320px] w-full max-w-[360px] [perspective:1100px]"
          onMouseMove={onMove}
          onMouseLeave={reset}
        >
          <motion.div
            className="absolute inset-0"
            style={{ rotateX: rotX, rotateY: rotY, transformStyle: "preserve-3d" }}
          >
            {PLANES.map((p) => (
              <Plane key={p.key} plane={p} spread={spread} />
            ))}
          </motion.div>
        </div>
      </div>
    </section>
  );
}
