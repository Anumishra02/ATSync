import Pill from "@/components/Pill";
import { cn } from "@/lib/utils";

// Four destinations, four pages -- "Features" used to share howitworks's
// key with a scroll-to hash, which meant two nav links pointed at the
// same route. They're genuinely separate pages now: how it works is the
// process (what happens when you upload), features is the product (what
// it's scored on and why).
const NAV = [
  { key: "howitworks", label: "How it works" },
  { key: "features", label: "Features" },
  { key: "coverletter", label: "Cover Letter" },
];

// Shared header. Fixed, 60px — pages still reserve pt-[60px]. `page` is
// the active route key; onNavigate(key) switches route; onHome() goes to
// the landing page (and resets the analyze flow); onCheckResume() goes
// straight to the upload page.
export default function Header({ page, onNavigate, onHome, onCheckResume }) {
  return (
    <header className="fixed inset-x-0 top-0 z-50 h-[60px] border-b border-hairline bg-stage/80 backdrop-blur-md">
      <div className="mx-auto flex h-full max-w-[1200px] items-center justify-between px-6 md:px-12">
        <button
          onClick={onHome}
          className="font-pixel text-lg tracking-tight text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring"
        >
          ATSync
        </button>

        <nav className="hidden items-center gap-7 md:flex">
          {NAV.map((item) => (
            <button
              key={item.key}
              onClick={() => onNavigate(item.key)}
              className={cn(
                "text-[13px] transition-colors duration-200 ease-stage hover:text-ink",
                "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring",
                page === item.key ? "text-ink" : "text-nav",
              )}
            >
              {item.label}
            </button>
          ))}
        </nav>

        <Pill onClick={onCheckResume}>Check Resume</Pill>
      </div>
    </header>
  );
}
