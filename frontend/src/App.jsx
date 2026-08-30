import { useRef, useState } from "react";
import { analyzeResume } from "@/lib/api";
import { SAMPLE_ANALYSIS } from "@/lib/sampleAnalysis";
import GlobalStyles from "@/components/GlobalStyles";
import Shell from "@/components/Shell";
import UploadPage from "@/pages/UploadPage";
import AnalysisProgressPage from "@/pages/AnalysisProgressPage";
import ResultsPage from "@/pages/ResultsPage";
import CoverLetterPage from "@/pages/CoverLetterPage";
import HowItWorksPage from "@/pages/HowItWorksPage";
import FeaturesPage from "@/pages/FeaturesPage";

// Route/state orchestrator. Two axes of state:
//   page    -- home | coverletter | howitworks | features
//   subPage -- upload | loading | results  (only meaningful when page === "home")
//
// Pages not yet rebuilt render inside <div className="legacy">, which
// scopes the old stylesheet so it can't fight the design tokens. The
// landing hero + fluid canvas (spec step 6) is not built yet; until it
// is, the upload page is the entry screen.
//
// Dev-only: ?mock=results:<quality|match|uncomputable> jumps straight to
// the results screen with a captured payload.
const MOCK = import.meta.env.DEV ? new URLSearchParams(window.location.search).get("mock") : null;
const mockAnalysis = MOCK?.startsWith("results:") ? SAMPLE_ANALYSIS[MOCK.split(":")[1]] ?? null : null;

// The five stages the progress readout walks through. The backend call is
// a single request (no streaming), so these advance on a timer while it's
// in flight, then snap to done when the response lands.
const STAGE_COUNT = 5;
const STAGE_INTERVAL_MS = 650;
const COLD_START_MS = 8000;

export default function App() {
  const [page, setPage] = useState("home");
  const [subPage, setSubPage] = useState(mockAnalysis ? "results" : "upload");
  const [file, setFile] = useState(null);
  const [jd, setJd] = useState("");
  const [stage, setStage] = useState(0);
  const [coldStart, setColdStart] = useState(false);
  const [analysis, setAnalysis] = useState(mockAnalysis);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const timers = useRef([]);

  const clearTimers = () => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  };

  const reset = () => {
    clearTimers();
    setSubPage("upload");
    setAnalysis(null);
    setFile(null);
    setJd("");
    setError("");
    setStage(0);
    setColdStart(false);
  };

  // Back to the upload form without wiping the file/JD -- used by the
  // results page's "add a job description" prompt.
  const editInputs = () => {
    setSubPage("upload");
    setError("");
  };

  const goHome = () => {
    setPage("home");
    reset();
  };

  const navigate = (key) => setPage(key);

  const handleAnalyze = async () => {
    if (!file) return setError("Choose a PDF resume first");
    setLoading(true);
    setError("");
    setSubPage("loading");
    setStage(0);
    setColdStart(false);
    clearTimers();

    // Walk the stages forward on a timer, holding at the last one until
    // the real response arrives.
    for (let i = 1; i < STAGE_COUNT; i++) {
      timers.current.push(setTimeout(() => setStage(i), i * STAGE_INTERVAL_MS));
    }
    timers.current.push(setTimeout(() => setColdStart(true), COLD_START_MS));

    try {
      const data = await analyzeResume(file, jd);
      clearTimers();
      setStage(STAGE_COUNT);
      setAnalysis(data);
      setSubPage("results");
    } catch (e) {
      clearTimers();
      setError(e.response?.data?.detail || "Something went wrong. The backend may be waking up — try again in a moment.");
      setSubPage("upload");
    }
    setLoading(false);
  };

  return (
    <>
      <GlobalStyles />
      <Shell page={page} onNavigate={navigate} onHome={goHome} showFooter={subPage !== "loading"}>
        {page === "coverletter" && (
          <div className="legacy">
            <CoverLetterPage onBack={goHome} />
          </div>
        )}
        {page === "howitworks" && (
          <div className="legacy">
            <HowItWorksPage onBack={goHome} />
          </div>
        )}
        {page === "features" && (
          <div className="legacy">
            <FeaturesPage onBack={goHome} />
          </div>
        )}

        {page === "home" && subPage === "upload" && (
          <UploadPage
            file={file}
            setFile={setFile}
            jd={jd}
            setJd={setJd}
            error={error}
            loading={loading}
            onAnalyze={handleAnalyze}
          />
        )}

        {page === "home" && subPage === "loading" && (
          <AnalysisProgressPage stage={stage} coldStart={coldStart} />
        )}

        {page === "home" && subPage === "results" && analysis && (
          <ResultsPage analysis={analysis} onReset={reset} onAddJd={editInputs} />
        )}
      </Shell>
    </>
  );
}
