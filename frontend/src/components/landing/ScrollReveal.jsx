import { motion } from "framer-motion";

const EASE = [0.22, 1, 0.36, 1];

// Fade + rise as a block scrolls into view. Once only. Honours
// prefers-reduced-motion via framer-motion's own reducedMotion handling
// plus the CSS backstop in index.css.
export default function ScrollReveal({ as = "div", delay = 0, y = 20, className, children, ...rest }) {
  const MotionTag = motion[as] || motion.div;
  return (
    <MotionTag
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-100px" }}
      transition={{ duration: 0.7, delay, ease: EASE }}
      className={className}
      {...rest}
    >
      {children}
    </MotionTag>
  );
}
