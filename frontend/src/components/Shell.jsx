import { TooltipProvider } from "@/components/ui/tooltip";
import Header from "@/components/Header";
import Footer from "@/components/Footer";

// App frame: tooltip context + fixed header + a main region that clears
// it. `showFooter` is off for the landing viewport (which is a single
// composition with the How-it-works page scrolling in below it) and on
// for every page people actually read.
export default function Shell({ page, onNavigate, onHome, showFooter = true, children }) {
  return (
    <TooltipProvider delayDuration={150}>
      <div className="flex min-h-screen flex-col bg-stage text-ink">
        <Header page={page} onNavigate={onNavigate} onHome={onHome} />
        <main className="flex flex-1 flex-col pt-[60px]">{children}</main>
        {showFooter && <Footer onNavigate={onNavigate} />}
      </div>
    </TooltipProvider>
  );
}
