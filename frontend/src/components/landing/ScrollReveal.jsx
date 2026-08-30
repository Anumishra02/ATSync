import { cn } from "@/lib/utils";

// Scroll-driven reveal: fade + rise + unblur as the block crosses into
// view, tracking scroll position continuously (native
// `animation-timeline: view()` -- see .sd-rise in index.css) so it reads
// smoother than an intersection-triggered tween. `delay` (kept for call
// sites that still pass it) staggers the scroll range rather than a
// timer. `scrub` opts into the symmetric version that also dissolves out
// the top. Falls back to plain visible content where unsupported.
export default function ScrollReveal({
  as = "div",
  delay = 0,
  scrub = false,
  className,
  children,
  style,
  ...rest
}) {
  const Tag = as;
  const offset = Math.min(delay * 45, 30);
  const merged =
    offset > 0
      ? {
          ...style,
          animationRange: scrub
            ? `entry ${4 + offset}% exit 98%`
            : `entry ${2 + offset}% cover ${32 + offset / 2}%`,
        }
      : style;

  return (
    <Tag className={cn(scrub ? "sd-scrub" : "sd-rise", className)} style={merged} {...rest}>
      {children}
    </Tag>
  );
}
