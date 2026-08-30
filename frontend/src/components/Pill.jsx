import { cn } from "@/lib/utils";

// The white pill CTA. One shape across the whole product. Sizes carry
// over from the previous site so nothing regresses: 13px text, 8/18
// padding, 8px radius for `md`; `lg` is the hero / results-header size.
const SIZES = {
  sm: "text-xs px-3.5 py-1.5 rounded-md gap-1.5",
  md: "text-[13px] px-[18px] py-2 rounded-lg gap-2",
  lg: "text-sm px-6 py-3 rounded-lg gap-2",
};

export default function Pill({ as: As = "button", size = "md", className, children, ...props }) {
  return (
    <As
      className={cn(
        "inline-flex items-center justify-center font-medium",
        "bg-pill text-pill-ink no-underline",
        "transition-[transform,opacity,box-shadow] duration-200 ease-stage",
        "hover:-translate-y-px hover:shadow-[0_8px_28px_-8px_rgba(250,250,250,0.35)]",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-pill",
        "disabled:pointer-events-none disabled:opacity-40",
        SIZES[size],
        className,
      )}
      {...props}
    >
      {children}
    </As>
  );
}
