import { DIMENSIONS } from "@/lib/constants";

// Step 7's second page. Was sharing a route with HowItWorksPage (a
// scroll-to hash on the same "howitworks" key) -- two nav links to one
// destination. This is the product page: what's scored, on what basis,
// and what's checked rather than estimated. Dimension copy is read from
// lib/constants.js's DIMENSIONS (the same data ResultsPage's
// DimensionRow renders), not duplicated here, so the results page and
// this one can't drift apart on what a dimension actually measures.
export default function FeaturesPage({ onBack }) {
  return (
    <div className="hiw-page fu">
      <button className="back-btn" onClick={onBack} style={{ marginBottom: 40 }}>
        ← Back to home
      </button>
      <div style={{ textAlign: "center", marginBottom: 64 }}>
        <div className="ai-badge" style={{ marginBottom: 20 }}>
          What ATSync does
        </div>
        <h1 className="hiw-title">
          Six dimensions, <span>on the record</span>
        </h1>
        <p className="hiw-sub">What each score is actually based on — not a keyword count, and not a black box.</p>
      </div>

      <div style={{ maxWidth: 760, margin: "0 auto" }}>
        <div className="section-card">
          <h2>🎯 The six scoring dimensions</h2>
          <p className="section-desc">
            100 points total. Relevance only runs when you supply a job description — see "Two modes" below.
          </p>
          {DIMENSIONS.map((d) => (
            <div
              key={d.key}
              className="check-row"
              style={{ flexDirection: "column", alignItems: "stretch", gap: 4, padding: "14px 0" }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", width: "100%" }}>
                <strong>{d.label}</strong>
                <span style={{ color: "var(--hint)", fontWeight: 600 }}>/{d.max}</span>
              </div>
              <p style={{ color: "var(--muted)", fontSize: 12.5, lineHeight: 1.55, margin: 0 }}>{d.measures}</p>
            </div>
          ))}
        </div>

        <div className="section-card">
          <h2>📬 Contact &amp; link verification</h2>
          <p className="section-desc">Checked, not estimated.</p>
          <div className="check-row">
            <span>Phone validity</span>
            <span style={{ color: "var(--muted)", fontSize: 12 }}>by region</span>
          </div>
          <div className="check-row">
            <span>Email deliverability</span>
            <span style={{ color: "var(--muted)", fontSize: 12 }}>MX lookup</span>
          </div>
          <div className="check-row">
            <span>Link reachability</span>
            <span style={{ color: "var(--muted)", fontSize: 12 }}>does it actually resolve</span>
          </div>
          <div className="check-row">
            <span>Unclickable-URL detection</span>
            <span style={{ color: "var(--muted)", fontSize: 12 }}>text with no href</span>
          </div>
          <div className="tip-box">
            💡 An unclickable URL looks like a link in the text but has no href behind it — invisible in your own
            PDF viewer, same as it is to an ATS.
          </div>
        </div>

        <div className="section-card">
          <h2>⚖️ Two modes</h2>
          <div className="check-row">
            <span>
              <strong>Quality</strong> — no job description
            </span>
            <strong>/85</strong>
          </div>
          <div className="check-row">
            <span>
              <strong>Match</strong> — job description supplied
            </span>
            <strong>/100</strong>
          </div>
          <p className="section-desc" style={{ marginTop: 12, marginBottom: 0 }}>
            The denominator is always stated — a quality-mode score is never silently measured against a full 100
            it never had a chance to reach.
          </p>
        </div>

        <div className="section-card">
          <h2>⚠️ What it won't guess</h2>
          <p className="section-desc">
            A dimension that can't be assessed is marked <strong>uncomputable</strong>, not scored 0 — a resume this
            system genuinely can't read on that dimension isn't the same as one it read and found empty.
          </p>
          <div className="tip-box">
            💡 Example: a resume with no bulleted content at all can't have Achievements assessed — there's nothing
            to check for quantified impact. Instead of a 0 (which would say "graded, and failed"), that dimension is
            marked uncomputable and the other five are reweighted so the score stays comparable — out of 80
            available points, not padded out to a full 100.
          </div>
        </div>

        <div className="section-card">
          <h2>✉️ Cover letter</h2>
          <p className="section-desc">Paste a job description, get a draft tailored to your resume.</p>
          <div className="check-row">
            <span>Job description</span>
            <span style={{ color: "var(--danger)", fontWeight: 600, fontSize: 13 }}>Required</span>
          </div>
          <p style={{ fontSize: 13, color: "var(--muted)", marginTop: 12, lineHeight: 1.6 }}>
            Without one, the result would be a generic template — so the product declines rather than producing
            something weak.
          </p>
          <div className="tip-box">
            💡 Generative, not evaluative: there's no rubric, no scoring, and no measurement behind a cover letter
            the way there is for the analysis above.
          </div>
        </div>
      </div>
    </div>
  );
}
