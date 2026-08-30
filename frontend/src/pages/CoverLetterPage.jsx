import { useState } from "react";
import { uploadResume, generateCoverLetter } from "@/lib/api";
import { COVER_LETTER_TONES } from "@/lib/constants";

export default function CoverLetterPage({ onBack }) {
  const [file, setFile] = useState(null);
  const [jd, setJd] = useState("");
  const [tone, setTone] = useState("professional");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  const handleGenerate = async () => {
    if (!file) return setError("Please upload your resume PDF");
    if (!jd.trim()) return setError("Please paste a job description");
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const uploaded = await uploadResume(file);
      const text = uploaded.full_text;
      if (!text || text.length < 10) {
        setError("Could not extract text from PDF.");
        setLoading(false);
        return;
      }
      const data = await generateCoverLetter({ resumeText: text, jobDescription: jd, tone });
      if (data && data.cover_letter) {
        setResult(data);
      } else {
        setError("Generation failed. Please try again.");
      }
    } catch (e) {
      setError(`Error: ${e.response?.data?.detail || e.message || "Something went wrong."}`);
    }
    setLoading(false);
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(result.cover_letter);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="cl-page">
      <div className="cl-left fu">
        <button className="back-btn" onClick={onBack}>
          ← Back to home
        </button>
        <div className="ai-badge">✦ AI Cover Letter Generator</div>
        <h1 className="cl-title">
          Generate your
          <br />
          <span style={{ color: "var(--accent)" }}>cover letter</span>
        </h1>
        <p className="cl-sub">
          Upload your resume and paste the job description. AI writes a tailored cover letter in seconds.
        </p>
        <div className="upload-card">
          <label className="field-label">Resume (PDF)</label>
          <div className="drop-zone" style={{ marginBottom: 18 }}>
            <input
              type="file"
              accept=".pdf"
              onChange={(e) => {
                setFile(e.target.files[0]);
                setResult(null);
              }}
            />
            <span className="drop-icon">📄</span>
            <p className="drop-text">{file ? "" : "Click to upload your resume"}</p>
            <p className="drop-hint">{file ? "" : "PDF only"}</p>
            {file && <p className="file-ok">✓ {file.name}</p>}
          </div>
          <label className="field-label">Job Description</label>
          <textarea
            rows={5}
            value={jd}
            onChange={(e) => setJd(e.target.value)}
            placeholder="Paste the full job description here..."
            style={{ marginBottom: 18 }}
          />
          <label className="field-label">Tone</label>
          <div className="tone-row">
            {COVER_LETTER_TONES.map((t) => (
              <button key={t} className={`tone-btn ${tone === t ? "active" : ""}`} onClick={() => setTone(t)}>
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </button>
            ))}
          </div>
          {error && <div className="error-msg">{error}</div>}
          <button className="btn btn-primary" onClick={handleGenerate} disabled={loading}>
            {loading ? (
              <>
                <div className="spinner" />
                Generating...
              </>
            ) : (
              "Generate Cover Letter →"
            )}
          </button>
          <p className="privacy">🔒 Your data is never stored</p>
        </div>
      </div>

      <div className="cl-right fu2">
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 20, color: "var(--text)" }}>Your Cover Letter</h2>
        <div className="cl-output">
          {/* Backend timeout for this call is 60s (services/cover_letter.py),
              plus a possible cold start on Render's free tier if the backend
              was idle. */}
          {loading && (
            <div className="cl-loading">
              <div className="cl-spinner" />
              <p className="cl-loading-text">Writing your cover letter with AI...</p>
              <p style={{ fontSize: 12, color: "var(--hint)", marginTop: 4 }}>
                Can take up to a minute -- longer on the first request if the server's been idle
              </p>
            </div>
          )}
          {!loading && !result && (
            <div className="cl-output-placeholder">
              <div className="cl-placeholder-icon">✉️</div>
              <p className="cl-placeholder-text">
                Your AI-generated cover letter
                <br />
                will appear here
              </p>
              <p style={{ fontSize: 12, color: "var(--hint)", marginTop: 8 }}>
                Upload resume + paste JD to get started
              </p>
            </div>
          )}
          {!loading && result && (
            <>
              <button className="copy-btn" onClick={handleCopy}>
                {copied ? "✓ Copied!" : "Copy"}
              </button>
              {result.subject_line && (
                <div className="cl-subject">
                  <span>Subject:</span>
                  {result.subject_line}
                </div>
              )}
              {result.key_points?.length > 0 && (
                <div className="cl-points">
                  <p
                    style={{
                      fontSize: 11,
                      fontWeight: 600,
                      color: "var(--hint)",
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                      marginBottom: 8,
                    }}
                  >
                    Key highlights
                  </p>
                  {result.key_points.map((p, i) => (
                    <div key={i} className="cl-point">
                      <div className="cl-point-dot" />
                      <span>{p}</span>
                    </div>
                  ))}
                </div>
              )}
              <div style={{ height: 1, background: "var(--border)", marginBottom: 20 }} />
              <p className="cl-letter">{result.cover_letter}</p>
              <div style={{ marginTop: 20, paddingTop: 16, borderTop: "0.5px solid var(--border)" }}>
                <p style={{ fontSize: 12, color: "var(--hint)" }}>
                  ~{result.word_count} words · {tone} tone
                </p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
