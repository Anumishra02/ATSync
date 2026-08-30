import ResumeVisual from "@/components/ResumeVisual";

// The "home / upload" viewport from the original App.js. Step 6 of the
// redesign replaces this with the near-black landing hero + fluid canvas,
// and step 5 splits the upload form onto its own page.
export default function LandingPage({ file, setFile, jd, setJd, error, loading, onAnalyze }) {
  return (
    <div className="hero-page">
      <div className="hero-left fu">
        <div className="ai-badge">✦ AI Powered · Free Resume Checker</div>
        <h1 className="hero-title">
          Is your resume
          <br />
          <span>good enough?</span>
        </h1>
        <p className="hero-sub">
          A free AI resume checker scoring Structure, Writing, Achievements, Skills, Experience, and Relevance to
          ensure your resume is ready to get you interview callbacks. A job description is optional.
        </p>
        <div className="upload-card">
          <label className="field-label">Resume (PDF)</label>
          <div className="drop-zone">
            <input type="file" accept=".pdf" onChange={(e) => setFile(e.target.files[0])} />
            <span className="drop-icon">📄</span>
            <p className="drop-text">{file ? "" : "Drop your resume here or choose a file"}</p>
            <p className="drop-hint">{file ? "" : "PDF only · Max 2MB"}</p>
            {file && <p className="file-ok">✓ {file.name}</p>}
          </div>
          <label className="field-label">
            Job Description{" "}
            <span style={{ textTransform: "none", fontWeight: 400, color: "var(--hint)" }}>(optional)</span>
          </label>
          <textarea
            rows={4}
            value={jd}
            onChange={(e) => setJd(e.target.value)}
            placeholder="Paste a job description to also score Relevance -- or leave blank for a quality-only score..."
          />
          {error && <div className="error-msg">{error}</div>}
          <button className="btn btn-primary" onClick={onAnalyze} disabled={loading}>
            {loading ? (
              <>
                <div className="spinner" />
                Analyzing...
              </>
            ) : (
              "Check My Resume →"
            )}
          </button>
          <p className="privacy">🔒 Privacy guaranteed · Your data is never stored</p>
        </div>
      </div>
      <div className="hero-right fu2">
        <ResumeVisual />
      </div>
    </div>
  );
}
