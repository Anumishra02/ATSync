const REPO_URL = "https://github.com/Anumishra02/ATSync";

// Restrained footer. No canvas, no marketing — just the honest pointers:
// the source, and where the measurement work is written up.
export default function Footer({ onNavigate }) {
  return (
    <footer className="border-t border-hairline bg-stage">
      <div className="mx-auto flex max-w-[1200px] flex-col gap-3 px-6 py-8 text-[13px] text-nav md:flex-row md:items-center md:justify-between md:px-12">
        <span className="font-pixel text-ink">ATSync</span>
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
          {/* Used to scroll to a "measured" anchor inside the combined
              howitworks page; that content now lives on its own Features
              page (the six dimensions, two modes, uncomputable state --
              literally what this link is named for), so it points there
              instead of at the process-only How it works page. */}
          <button
            onClick={() => onNavigate?.("features")}
            className="transition-colors duration-200 ease-stage hover:text-ink"
          >
            How it was measured
          </button>
          <a
            href={REPO_URL}
            target="_blank"
            rel="noreferrer"
            className="transition-colors duration-200 ease-stage hover:text-ink"
          >
            Source
          </a>
        </div>
        <span className="text-subtle">Scores are estimates against a human-graded rubric.</span>
      </div>
    </footer>
  );
}
