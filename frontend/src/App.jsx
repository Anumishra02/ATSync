import { useState } from "react";
import { analyzeResume } from "@/lib/api";
import { SAMPLE_ANALYSIS } from "@/lib/sampleAnalysis";
import GlobalStyles from "@/components/GlobalStyles";
import Shell from "@/components/Shell";
import LandingPage from "@/pages/LandingPage";
import AnalysisProgressPage from "@/pages/AnalysisProgressPage";
import ResultsPage from "@/pages/ResultsPage";
import CoverLetterPage from "@/pages/CoverLetterPage";
import HowItWorksPage from "@/pages/HowItWorksPage";
import FeaturesPage from "@/pages/FeaturesPage";

// Route/state orchestrator. Two axes of state:
//   page    -- home | coverletter | howitworks | features
//   subPage -- upload | loading | results  (only meaningful when page === "home")
//
// The redesign is landing on a page at a time (see the spec's build
// order). Pages not yet rebuilt render inside <div className="legacy">,
// which scopes the old stylesheet so it can't fight the design tokens.
// Dev-only: ?mock=results:<quality|match|uncomputable> jumps straight to
// the results screen with a captured payload, so the redesign work
// doesn't need a running backend + a real upload on every reload.
const MOCK = import.meta.env.DEV ? new URLSearchParams(window.location.search).get("mock") : null;
const mockAnalysis = MOCK?.startsWith("results:") ? SAMPLE_ANALYSIS[MOCK.split(":")[1]] ?? null : null;

export default function App() {
  const [page, setPage] = useState("home");
  const [subPage, setSubPage] = useState(mockAnalysis ? "results" : "upload");
  const [file, setFile] = useState(null);
  const [jd, setJd] = useState("");
  const [loadStep, setLoadStep] = useState(0);
  const [analysis, setAnalysis] = useState(mockAnalysis);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const reset = () => {
    setSubPage("upload");
    setAnalysis(null);
    setFile(null);
    setJd("");
    setError("");
    setLoadStep(0);
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
    if (!file) return setError("Please upload a PDF resume");
    setLoading(true);
    setError("");
    setSubPage("loading");
    setLoadStep(0);
    try {
      // Job description is optional -- analyzeResume only appends it when
      // non-blank, so /v2/analyze runs in quality mode without one.
      setLoadStep(1);
      const analyzePromise = analyzeResume(file, jd);
      await new Promise((r) => setTimeout(r, 700));
      setLoadStep(2);
      await new Promise((r) => setTimeout(r, 700));
      setLoadStep(3);
      await new Promise((r) => setTimeout(r, 700));
      setLoadStep(4);
      const data = await analyzePromise;
      setAnalysis(data);
      setSubPage("results");
    } catch (e) {
      setError(e.response?.data?.detail || "Something went wrong. Make sure backend is running.");
      setSubPage("upload");
    }
    setLoading(false);
  };

  const isLanding = page === "home" && subPage === "upload";

  return (
    <>
      <GlobalStyles />
      <Shell page={page} onNavigate={navigate} onHome={goHome} showFooter={!isLanding}>
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

        {page === "home" && (subPage === "upload" || subPage === "loading") && (
          <div className="legacy">
            {subPage === "upload" && (
              <LandingPage
                file={file}
                setFile={setFile}
                jd={jd}
                setJd={setJd}
                error={error}
                loading={loading}
                onAnalyze={handleAnalyze}
              />
            )}
            {subPage === "loading" && <AnalysisProgressPage loadStep={loadStep} />}
          </div>
        )}

        {page === "home" && subPage === "results" && analysis && (
          <ResultsPage analysis={analysis} onReset={reset} onAddJd={editInputs} />
        )}
      </Shell>
    </>
  );
}
