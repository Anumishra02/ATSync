import { cn } from "@/lib/utils";

// Ghost text link — the quieter half of a CTA pair ("How it works").
export default function GhostLink({ as: As = "button", className, children, ...props }) {
  return (
    <As
      className={cn(
        "group inline-flex items-center gap-1.5 text-[13px] font-medium text-nav no-underline",
        "transition-colors duration-200 ease-stage hover:text-ink",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
        className,
      )}
      {...props}
    >
      {children}
    </As>
  );
}
