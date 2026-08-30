import { LOAD_STEPS } from "@/lib/constants";

// The "loading" viewport from the original App.js. Step 5 of the redesign
// replaces this with the dot-matrix progress readout wired to the real
// backend stages (parse / sections / skills / scoring / verification).
export default function AnalysisProgressPage({ loadStep }) {
  return (
    <div className="loading-page">
      <div className="loading-left">
        <p style={{ fontSize: 13, color: "var(--muted)", fontWeight: 500, marginBottom: 16 }}>Your Score</p>
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 24 }}>
          <div style={{ width: 90, height: 90, borderRadius: "50%", background: "#f0f0ee" }} />
        </div>
        {["CONTENT", "SECTIONS", "ATS ESSENTIALS", "TAILORING"].map((label) => (
          <div key={label} style={{ marginBottom: 16 }}>
            <p style={{ fontSize: 10, color: "var(--hint)", fontWeight: 600, marginBottom: 6 }}>{label}</p>
            <div className="skeleton" style={{ width: "80%" }} />
            <div className="skeleton" style={{ width: "60%" }} />
          </div>
        ))}
      </div>
      <div className="loading-right">
        <div className="checklist">
          <h2 style={{ fontSize: 22, fontWeight: 600, marginBottom: 32, letterSpacing: "-0.02em" }}>
            Analyzing your resume...
          </h2>
          {LOAD_STEPS.map((label, i) => {
            const status = i < loadStep ? "done" : i === loadStep ? "active" : "pending";
            return (
              <div key={i} className="check-item">
                <div className={`check-icon ${status}`}>
                  {status === "done" ? (
                    "✓"
                  ) : status === "active" ? (
                    <div
                      style={{
                        width: 16,
                        height: 16,
                        border: "2px solid var(--info)",
                        borderTopColor: "transparent",
                        borderRadius: "50%",
                        animation: "spin 0.8s linear infinite",
                      }}
                    />
                  ) : (
                    ""
                  )}
                </div>
                <span className={`check-label ${status}`}>{label}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
