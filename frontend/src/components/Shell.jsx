import { TooltipProvider } from "@/components/ui/tooltip";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import { cn } from "@/lib/utils";

// App frame: tooltip context + fixed header + a main region that clears
// it. `showFooter` is off for the landing viewport (a single composition,
// no footer). `bare` drops the opaque stage background so the landing's
// fixed fluid canvas shows through -- the body itself is already
// --bg (#050505), so nothing goes light.
export default function Shell({
  page,
  onNavigate,
  onHome,
  onCheckResume,
  showFooter = true,
  bare = false,
  children,
}) {
  return (
    <TooltipProvider delayDuration={150}>
      <div className={cn("flex min-h-screen flex-col text-ink", !bare && "bg-stage")}>
        <Header page={page} onNavigate={onNavigate} onHome={onHome} onCheckResume={onCheckResume} />
        <main className="flex flex-1 flex-col pt-[60px]">{children}</main>
        {showFooter && <Footer onNavigate={onNavigate} />}
      </div>
    </TooltipProvider>
  );
}
