// Content lifted verbatim from the original App.js. Step 7 of the
// redesign rewrites this page's copy and sections against the real
// pipeline (two modes, six dimensions, the uncomputable worked example,
// verified checks, how it was measured).
const steps = [
  {
    num: "01",
    title: "Upload your resume",
    desc: "Drag and drop your PDF resume into the analyzer. Our system instantly extracts and parses all content — work experience, skills, education, and contact info.",
    card: [
      { icon: "📄", text: "PDF format supported" },
      { icon: "⚡", text: "Instant text extraction" },
      { icon: "🔒", text: "Your data is never stored" },
    ],
  },
  {
    num: "02",
    title: "Paste the job description",
    desc: "Copy the full job description from LinkedIn, Indeed, or any job board and paste it in. The more detailed the JD, the more accurate your ATS score will be.",
    card: [
      { icon: "🎯", text: "Keyword extraction from JD" },
      { icon: "🔍", text: "Skill gap identification" },
      { icon: "📊", text: "Match percentage calculated" },
    ],
  },
  {
    num: "03",
    title: "AI analyzes your resume",
    desc: "Our AI runs 7 crucial checks — ATS score, quantified impact, repetition, contact info, file format, section completeness, and spelling & grammar.",
    card: [
      { icon: "🤖", text: "Powered by Google Gemini AI" },
      { icon: "✅", text: "7 checks in under 10 seconds" },
      { icon: "📈", text: "Weighted overall score generated" },
    ],
  },
  {
    num: "04",
    title: "Review detailed results",
    desc: "Get a full breakdown of every check with specific issues found, your score per category, and actionable tips to fix each problem.",
    card: [
      { icon: "📋", text: "Category-by-category breakdown" },
      { icon: "💡", text: "Specific improvement tips" },
      { icon: "🏆", text: "Overall score out of 100" },
    ],
  },
  {
    num: "05",
    title: "Generate cover letter",
    desc: "Use the Cover Letter Generator to create a tailored, professional cover letter based on your resume and the job description — in your chosen tone.",
    card: [
      { icon: "✉️", text: "AI-written in seconds" },
      { icon: "🎨", text: "5 tone options to choose from" },
      { icon: "📋", text: "One-click copy to clipboard" },
    ],
  },
  {
    num: "06",
    title: "Apply with confidence",
    desc: "With an optimized resume and a polished cover letter, you're ready to apply. Track your improvements by re-analyzing after making changes.",
    card: [
      { icon: "🚀", text: "ATS-optimized resume" },
      { icon: "📩", text: "Tailored cover letter ready" },
      { icon: "🎯", text: "Higher interview callback rate" },
    ],
  },
];

export default function HowItWorksPage({ onBack }) {
  return (
    <div className="hiw-page fu">
      <button className="back-btn" onClick={onBack} style={{ marginBottom: 40 }}>
        ← Back to home
      </button>
      <div style={{ textAlign: "center", marginBottom: 64 }}>
        <div className="ai-badge" style={{ marginBottom: 20 }}>
          How it works
        </div>
        <h1 className="hiw-title">
          From upload to <span>offer letter</span>
        </h1>
        <p className="hiw-sub">6 simple steps to get your resume ATS-ready and land more interviews</p>
      </div>
      <div className="hiw-steps">
        {steps.map((step, i) => (
          <div key={i} className="hiw-step fu" style={{ animationDelay: `${i * 0.08}s` }}>
            <div className="hiw-step-left">
              <div className="hiw-num">{step.num}</div>
              <div className="hiw-line" />
            </div>
            <div className="hiw-content">
              <h3 className="hiw-step-title">{step.title}</h3>
              <p className="hiw-step-desc">{step.desc}</p>
              <div className="hiw-step-card">
                {step.card.map((row, j) => (
                  <div key={j} className="hiw-step-card-row">
                    <span className="hiw-icon">{row.icon}</span>
                    <span>{row.text}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
