import { useState } from "react";
import axios from "axios";

const API = "http://127.0.0.1:8000/api/resume";

const s = {
  app: { minHeight: "100vh", background: "#0f0f1a", color: "#fff", fontFamily: "Inter, sans-serif", padding: "24px" },
  center: { maxWidth: "800px", margin: "0 auto" },
  header: { textAlign: "center", marginBottom: "40px" },
  h1: { fontSize: "2.5rem", fontWeight: "800", background: "linear-gradient(135deg, #6366f1, #8b5cf6, #06b6d4)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", marginBottom: "8px" },
  subtitle: { color: "#94a3b8", fontSize: "1rem" },
  card: { background: "#1e1e2e", borderRadius: "20px", padding: "32px", marginBottom: "20px", border: "1px solid #2d2d3d" },
  label: { display: "block", color: "#94a3b8", fontSize: "0.85rem", marginBottom: "8px", fontWeight: "500" },
  fileInput: { width: "100%", color: "#cbd5e1", fontSize: "0.9rem", padding: "12px", background: "#0f0f1a", border: "1px solid #2d2d3d", borderRadius: "12px", cursor: "pointer" },
  textarea: { width: "100%", background: "#0f0f1a", border: "1px solid #2d2d3d", borderRadius: "12px", padding: "16px", color: "#e2e8f0", fontSize: "0.9rem", resize: "none", outline: "none", boxSizing: "border-box" },
  btn: { width: "100%", padding: "14px", borderRadius: "12px", border: "none", fontWeight: "700", fontSize: "1rem", cursor: "pointer", transition: "all 0.2s" },
  btnPrimary: { background: "linear-gradient(135deg, #6366f1, #8b5cf6)", color: "#fff" },
  btnSecondary: { background: "#2d2d3d", color: "#fff" },
  btnPurple: { background: "linear-gradient(135deg, #8b5cf6, #ec4899)", color: "#fff" },
  error: { color: "#f87171", fontSize: "0.85rem", marginTop: "8px" },
  scoreNum: (score) => ({ fontSize: "5rem", fontWeight: "900", color: score >= 80 ? "#4ade80" : score >= 60 ? "#facc15" : score >= 40 ? "#fb923c" : "#f87171" }),
  grade: { fontSize: "1.5rem", fontWeight: "700", marginTop: "8px" },
  verdict: { color: "#94a3b8", fontSize: "0.9rem", marginTop: "4px" },
  summary: { color: "#64748b", fontSize: "0.8rem", marginTop: "12px" },
  sectionTitle: (color) => ({ color, fontWeight: "700", fontSize: "1.1rem", marginBottom: "16px" }),
  tagRow: { display: "flex", flexWrap: "wrap", gap: "8px" },
  tag: (bg, color) => ({ background: bg, color, padding: "6px 14px", borderRadius: "999px", fontSize: "0.8rem", fontWeight: "500" }),
  grid2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" },
  qCard: { background: "#0f0f1a", borderRadius: "12px", padding: "16px", marginBottom: "12px", border: "1px solid #2d2d3d" },
  qText: { color: "#e2e8f0", fontSize: "0.9rem", lineHeight: "1.6" },
  steps: { display: "flex", justifyContent: "center", gap: "8px", marginBottom: "32px", alignItems: "center" },
  step: (active) => ({ padding: "6px 20px", borderRadius: "999px", fontSize: "0.8rem", fontWeight: "600", background: active ? "linear-gradient(135deg, #6366f1, #8b5cf6)" : "#2d2d3d", color: active ? "#fff" : "#64748b" }),
  stepLine: { width: "40px", height: "2px", background: "#2d2d3d" },
};

export default function App() {
  const [step, setStep] = useState("upload");
  const [file, setFile] = useState(null);
  const [jd, setJd] = useState("");
  const [resumeText, setResumeText] = useState("");
  const [scoreData, setScoreData] = useState(null);
  const [questions, setQuestions] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleUpload = async () => {
    if (!file) return setError("Please select a PDF file");
    if (!jd.trim()) return setError("Please paste a job description");
    setLoading(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await axios.post(`${API}/upload`, formData);
      const text = res.data.full_text;
      setResumeText(text);
      const scoreRes = await axios.post(`${API}/score`, {
        resume_text: text,
        job_description: jd,
      });
      setScoreData(scoreRes.data);
      setStep("score");
    } catch (e) {
      setError("Something went wrong. Is the backend running?");
    }
    setLoading(false);
  };

  const handleGetQuestions = async () => {
    if (!resumeText || !jd) {
      setError("Missing resume text or job description");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await axios.post(`${API}/interview-questions`, {
        resume_text: resumeText,
        job_description: jd,
      });
      setQuestions(res.data);
      setStep("questions");
    } catch (e) {
      setError(`Failed: ${e.response?.data?.detail || e.message}`);
    }
    setLoading(false);
  };

  const reset = () => {
    setStep("upload");
    setScoreData(null);
    setQuestions(null);
    setFile(null);
    setJd("");
    setResumeText("");
    setError("");
  };

  return (
    <div style={s.app}>
      <div style={s.center}>

        {/* Header */}
        <div style={s.header}>
          <h1 style={s.h1}>AI Resume Analyzer</h1>
          <p style={s.subtitle}>Upload your resume · Get ATS score · Generate interview questions</p>
        </div>

        {/* Step Indicators */}
        <div style={s.steps}>
          <div style={s.step(step === "upload")}>1. Upload</div>
          <div style={s.stepLine} />
          <div style={s.step(step === "score")}>2. ATS Score</div>
          <div style={s.stepLine} />
          <div style={s.step(step === "questions")}>3. Interview Prep</div>
        </div>

        {/* STEP 1 — Upload */}
        {step === "upload" && (
          <div style={s.card}>
            <div style={{ marginBottom: "24px" }}>
              <label style={s.label}>📄 Upload Resume (PDF)</label>
              <input type="file" accept=".pdf"
                onChange={(e) => setFile(e.target.files[0])}
                style={s.fileInput} />
              {file && <p style={{ color: "#4ade80", fontSize: "0.8rem", marginTop: "6px" }}>✅ {file.name} selected</p>}
            </div>
            <div style={{ marginBottom: "24px" }}>
              <label style={s.label}>📋 Paste Job Description</label>
              <textarea rows={7} value={jd}
                onChange={(e) => setJd(e.target.value)}
                placeholder="Paste the full job description here..."
                style={s.textarea} />
            </div>
            {error && <p style={s.error}>{error}</p>}
            <button onClick={handleUpload} disabled={loading}
              style={{ ...s.btn, ...s.btnPrimary, opacity: loading ? 0.7 : 1 }}>
              {loading ? "⏳ Analyzing your resume..." : "🚀 Analyze Resume"}
            </button>
          </div>
        )}

        {/* STEP 2 — Score */}
        {step === "score" && scoreData && (
          <div>
            {/* Score Card */}
            <div style={{ ...s.card, textAlign: "center" }}>
              <p style={{ color: "#94a3b8", fontSize: "0.85rem", marginBottom: "8px" }}>YOUR ATS SCORE</p>
              <p style={s.scoreNum(scoreData.ats_score)}>{scoreData.ats_score}%</p>
              <p style={s.grade}>{scoreData.grade}</p>
              <p style={s.verdict}>{scoreData.verdict}</p>
              <p style={s.summary}>{scoreData.summary}</p>

              {/* Score bar */}
              <div style={{ background: "#0f0f1a", borderRadius: "999px", height: "8px", marginTop: "20px", overflow: "hidden" }}>
                <div style={{ width: `${scoreData.ats_score}%`, height: "100%", borderRadius: "999px",
                  background: scoreData.ats_score >= 80 ? "#4ade80" : scoreData.ats_score >= 60 ? "#facc15" : "#f87171",
                  transition: "width 1s ease" }} />
              </div>
            </div>

            {/* Matched Skills */}
            <div style={s.card}>
              <p style={s.sectionTitle("#4ade80")}>✅ Matched Skills ({scoreData.matched_skills.length})</p>
              <div style={s.tagRow}>
                {scoreData.matched_skills.map((sk) => (
                  <span key={sk} style={s.tag("#14532d", "#4ade80")}>{sk}</span>
                ))}
              </div>
            </div>

            {/* Missing Skills */}
            <div style={s.card}>
              <p style={s.sectionTitle("#f87171")}>❌ Missing Skills ({scoreData.missing_skills.length})</p>
              <div style={s.tagRow}>
                {scoreData.missing_skills.map((sk) => (
                  <span key={sk} style={s.tag("#7f1d1d", "#f87171")}>{sk}</span>
                ))}
              </div>
              {scoreData.missing_skills.length > 0 && (
                <p style={{ color: "#64748b", fontSize: "0.8rem", marginTop: "16px" }}>
                  💡 Add these skills to your resume to increase your ATS score
                </p>
              )}
            </div>

            {/* Buttons */}
            <div style={s.grid2}>
              <button onClick={handleGetQuestions} disabled={loading}
                style={{ ...s.btn, ...s.btnPurple, opacity: loading ? 0.7 : 1 }}>
                {loading ? "⏳ Generating..." : "🎯 Get Interview Questions"}
              </button>
              <button onClick={reset} style={{ ...s.btn, ...s.btnSecondary }}>
                🔄 Analyze Another
              </button>
            </div>
            {error && <p style={{ ...s.error, marginTop: "12px" }}>{error}</p>}
          </div>
        )}

        {/* STEP 3 — Questions */}
        {step === "questions" && questions && (
          <div>
            <div style={{ ...s.card, background: "linear-gradient(135deg, #1e1b4b, #2d1b69)", marginBottom: "24px" }}>
              <h2 style={{ fontSize: "1.5rem", fontWeight: "800", color: "#c4b5fd" }}>🎯 Your Personalized Interview Prep</h2>
              <p style={{ color: "#a78bfa", fontSize: "0.85rem", marginTop: "4px" }}>Questions tailored specifically to your resume and target role</p>
            </div>

            {/* Technical */}
            <div style={s.card}>
              <p style={s.sectionTitle("#60a5fa")}>💻 Technical Questions</p>
              {questions.technical_questions?.map((q, i) => (
                <div key={i} style={s.qCard}>
                  <p style={{ color: "#94a3b8", fontSize: "0.75rem", marginBottom: "6px" }}>Q{i + 1}</p>
                  <p style={s.qText}>{q.question}</p>
                  <div style={{ display: "flex", gap: "8px", marginTop: "10px" }}>
                    <span style={s.tag("#1e3a5f", "#60a5fa")}>{q.topic}</span>
                    <span style={s.tag(
                      q.difficulty === "hard" ? "#7f1d1d" : q.difficulty === "medium" ? "#78350f" : "#14532d",
                      q.difficulty === "hard" ? "#f87171" : q.difficulty === "medium" ? "#fbbf24" : "#4ade80"
                    )}>{q.difficulty}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Project */}
            <div style={s.card}>
              <p style={s.sectionTitle("#fbbf24")}>🚀 Project-Based Questions</p>
              {questions.project_questions?.map((q, i) => (
                <div key={i} style={s.qCard}>
                  <p style={{ color: "#94a3b8", fontSize: "0.75rem", marginBottom: "6px" }}>Q{i + 1}</p>
                  <p style={s.qText}>{q.question}</p>
                  <span style={{ ...s.tag("#78350f", "#fbbf24"), display: "inline-block", marginTop: "8px" }}>{q.project}</span>
                </div>
              ))}
            </div>

            {/* Behavioral */}
            <div style={s.card}>
              <p style={s.sectionTitle("#f472b6")}>🧠 Behavioral Questions</p>
              {questions.behavioral_questions?.map((q, i) => (
                <div key={i} style={s.qCard}>
                  <p style={{ color: "#94a3b8", fontSize: "0.75rem", marginBottom: "6px" }}>Q{i + 1}</p>
                  <p style={s.qText}>{q.question}</p>
                  <span style={{ ...s.tag("#831843", "#f472b6"), display: "inline-block", marginTop: "8px" }}>{q.competency}</span>
                </div>
              ))}
            </div>

            {/* Tips */}
            <div style={s.card}>
              <p style={s.sectionTitle("#4ade80")}>💡 Interview Tips</p>
              {questions.tips?.map((tip, i) => (
                <div key={i} style={{ display: "flex", gap: "12px", marginBottom: "12px", alignItems: "flex-start" }}>
                  <span style={{ color: "#4ade80", fontWeight: "700" }}>{i + 1}.</span>
                  <p style={{ color: "#cbd5e1", fontSize: "0.9rem", lineHeight: "1.6" }}>{tip}</p>
                </div>
              ))}
            </div>

            <button onClick={reset} style={{ ...s.btn, ...s.btnSecondary }}>
              🔄 Start Over
            </button>
          </div>
        )}

      </div>
    </div>
  );
}