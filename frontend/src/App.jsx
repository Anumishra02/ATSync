import { useState } from "react";
import { analyzeResume } from "@/lib/api";
import GlobalStyles from "@/components/GlobalStyles";
import Shell from "@/components/Shell";
import LandingPage from "@/pages/LandingPage";
import AnalysisProgressPage from "@/pages/AnalysisProgressPage";
import ResultsPage from "@/pages/ResultsPage";
import CoverLetterPage from "@/pages/CoverLetterPage";
import HowItWorksPage from "@/pages/HowItWorksPage";

// Route/state orchestrator. Two axes of state:
//   page    -- home | coverletter | howitworks
//   subPage -- upload | loading | results  (only meaningful when page === "home")
//
// The redesign is landing on a page at a time (see the spec's build
// order). Pages not yet rebuilt render inside <div className="legacy">,
// which scopes the old stylesheet so it can't fight the design tokens.
export default function App() {
  const [page, setPage] = useState("home");
  const [subPage, setSubPage] = useState("upload");
  const [file, setFile] = useState(null);
  const [jd, setJd] = useState("");
  const [loadStep, setLoadStep] = useState(0);
  const [analysis, setAnalysis] = useState(null);
  const [activeCategory, setActiveCategory] = useState("structure");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const reset = () => {
    setSubPage("upload");
    setAnalysis(null);
    setFile(null);
    setJd("");
    setError("");
    setLoadStep(0);
    setActiveCategory("structure");
  };

  const goHome = () => {
    setPage("home");
    reset();
  };

  const navigate = (key, hash) => {
    setPage(key);
    if (hash) {
      // section anchors land in step 7 when How-it-works is built; until
      // then this is just a route switch.
      requestAnimationFrame(() => document.getElementById(hash)?.scrollIntoView({ behavior: "smooth" }));
    }
  };

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

        {page === "home" && (
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
            {subPage === "results" && analysis && (
              <ResultsPage
                analysis={analysis}
                activeCategory={activeCategory}
                setActiveCategory={setActiveCategory}
                onReset={reset}
              />
            )}
          </div>
        )}
      </Shell>
    </>
  );
}
