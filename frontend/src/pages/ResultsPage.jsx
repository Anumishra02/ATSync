import ScoreCircle from "@/components/ScoreCircle";
import DimensionSection, { StatusBadge } from "@/components/DimensionSection";
import { DIMENSIONS } from "@/lib/constants";
import { scoreColor } from "@/lib/score";

// The "results" viewport from the original App.js. Step 4 of the redesign
// rebuilds this as the primary screen: explicit denominator in the score
// header, all six dimensions as rows with the three-state treatment, and
// a dedicated Contact & Links section styled as verified findings.
export default function ResultsPage({ analysis, activeCategory, setActiveCategory, onReset }) {
  const activeDim = analysis.dimensions.find((d) => d.dimension === activeCategory);

  return (
    <div className="results-page">
      <div className="results-left">
        <div className="score-box">
          <p className="score-box-label">Your Score</p>
          <p className="score-box-num" style={{ color: scoreColor(analysis.score) }}>
            {analysis.score}
          </p>
          <div style={{ display: "flex", justifyContent: "center", margin: "10px 0 4px" }}>
            <ScoreCircle score={analysis.score} size={110} />
          </div>
          {/* available_points, not a flat /100: in quality mode Relevance
              is not_applicable and its points aren't available at all, so
              the honest denominator is what actually ran. */}
          <p className="score-box-sub">
            {analysis.raw_score} / {analysis.available_points} points earned
          </p>
          <p className="score-box-sub" style={{ marginTop: 4 }}>
            {analysis.mode === "match"
              ? "Match mode — scored against your job description"
              : "Quality mode — no job description supplied"}
          </p>
        </div>
        <p
          style={{
            fontSize: 10,
            fontWeight: 600,
            color: "var(--hint)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            margin: "16px 0 8px 4px",
          }}
        >
          Dimensions
        </p>
        {DIMENSIONS.map(({ key, label, icon }) => {
          const dim = analysis.dimensions.find((d) => d.dimension === key);
          return (
            <div
              key={key}
              className={`cat-item ${activeCategory === key ? "active" : ""}`}
              onClick={() => setActiveCategory(key)}
            >
              <span className="cat-left">
                {icon} {label}
              </span>
              {activeCategory !== key && <StatusBadge dim={dim} />}
            </div>
          );
        })}
        <button className="back-btn" onClick={onReset} style={{ marginTop: 20, paddingLeft: 12 }}>
          ← Analyze another
        </button>
      </div>
      <div className="results-right">
        <button className="back-btn" onClick={onReset}>
          ← Back
        </button>
        {activeDim && <DimensionSection dim={activeDim} />}
      </div>
    </div>
  );
}
