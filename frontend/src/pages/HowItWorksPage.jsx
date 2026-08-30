// Step 7 of the redesign. Rewritten against the real /v2/analyze pipeline
// instead of the original 6-step marketing copy -- and split from the
// product-capability content, which now has its own page (FeaturesPage).
// This page is the process: four steps, sequential, mirroring the labels
// the progress screen itself shows while a resume is actually running
// through it (see pages/AnalysisProgressPage.jsx's step labels).
const steps = [
  {
    num: "01",
    title: "Parse",
    desc: "Your PDF is read three ways at once: the text layer, any hyperlink annotations (an icon-only email or LinkedIn link the text alone would never show), and how that maps onto sections — Experience, Skills, Education, and the rest.",
    card: [
      { icon: "📄", text: "Text layer + hyperlink annotations" },
      { icon: "🔗", text: "Catches icon-only links plain text misses" },
      { icon: "📋", text: "Sections identified from real headings" },
    ],
  },
  {
    num: "02",
    title: "Score",
    desc: "Six dimensions, each checked against a fixed rubric — not a keyword count. See Features for exactly what each one measures and how many points it's worth.",
    card: [
      { icon: "🎯", text: "Six rubric dimensions, 100 points" },
      { icon: "🧭", text: "Relevance only runs with a job description" },
      { icon: "⚖️", text: "Full breakdown on the Features page" },
    ],
  },
  {
    num: "03",
    title: "Verify",
    desc: "Contact info and links are checked, not estimated: phone validity by region, email deliverability by MX lookup, and whether your links actually resolve.",
    card: [
      { icon: "📞", text: "Phone validity by region" },
      { icon: "📧", text: "Email deliverability (MX lookup)" },
      { icon: "🔗", text: "Link reachability" },
    ],
  },
  {
    num: "04",
    title: "Report",
    desc: "Your score, the points it's actually out of, and — honestly — any dimension it couldn't assess, instead of a silent zero.",
    card: [
      { icon: "🏆", text: "Score with its real denominator" },
      { icon: "⚠️", text: "Uncomputable dimensions shown as such" },
      { icon: "📋", text: "Per-dimension detail on request" },
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
          What happens when you <span>upload a resume</span>
        </h1>
        <p className="hiw-sub">Four steps, in order — the same ones the progress screen shows while it runs.</p>
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
