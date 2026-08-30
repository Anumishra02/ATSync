import { useState } from "react";
import { analyzeResume } from "@/lib/api";
import GlobalStyles from "@/components/GlobalStyles";
import Header from "@/components/Header";
import LandingPage from "@/pages/LandingPage";
import AnalysisProgressPage from "@/pages/AnalysisProgressPage";
import ResultsPage from "@/pages/ResultsPage";
import CoverLetterPage from "@/pages/CoverLetterPage";
import HowItWorksPage from "@/pages/HowItWorksPage";

// Route/state orchestrator. Behaviour is carried over unchanged from the
// original single-file App.js during the split (step 2); the redesign
// replaces each page's internals in later steps. Two axes of state:
//   page    -- home | coverletter | howitworks
//   subPage -- upload | loading | results  (only meaningful when page === "home")
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

  return (
    <>
      <GlobalStyles />
      <Header page={page} onNavigate={setPage} onHome={goHome} />

      {page === "coverletter" && <CoverLetterPage onBack={() => setPage("home")} />}
      {page === "howitworks" && <HowItWorksPage onBack={() => setPage("home")} />}

      {page === "home" && (
        <>
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
        </>
      )}
    </>
  );
}
