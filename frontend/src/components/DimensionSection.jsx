import { DIMENSIONS, STATUS_META } from "@/lib/constants";
import { scoreColor } from "@/lib/score";

export function StatusBadge({ dim }) {
  if (!dim || dim.status !== "scored") {
    return (
      <span className="cat-badge" style={{ background: "#f5f5f4", color: "var(--hint)" }}>
        {STATUS_META[dim?.status || "uncomputable"].label}
      </span>
    );
  }
  const pct = dim.max_points ? (dim.score / dim.max_points) * 100 : 0;
  const color = pct >= 80 ? "#16a34a" : pct >= 60 ? "#d97706" : "#dc2626";
  const bg = pct >= 80 ? "#f0fdf4" : pct >= 60 ? "#fffbeb" : "#fef2f2";
  return (
    <span className="cat-badge" style={{ background: bg, color }}>
      {dim.score}/{dim.max_points}
    </span>
  );
}

export default function DimensionSection({ dim }) {
  const meta = DIMENSIONS.find((d) => d.key === dim.dimension) || {};
  const pct = dim.status === "scored" && dim.max_points ? (dim.score / dim.max_points) * 100 : 0;
  const detailEntries =
    dim.status === "scored" && dim.detail
      ? Object.entries(dim.detail).filter(([, v]) => typeof v !== "object")
      : [];
  return (
    <div className="section-card">
      <h2>
        {meta.icon} {meta.label || dim.dimension}
      </h2>
      <p className="section-desc">{meta.desc}</p>
      {dim.status === "scored" ? (
        <>
          <div className="score-bar-track">
            <div className="score-bar-fill" style={{ width: `${pct}%`, background: scoreColor(pct) }} />
          </div>
          <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 14 }}>
            {dim.score} / {dim.max_points} points
          </p>
          {detailEntries.map(([k, v]) => (
            <div key={k} className="check-row">
              <span style={{ textTransform: "capitalize" }}>{k.replace(/_/g, " ")}</span>
              <strong>{String(v)}</strong>
            </div>
          ))}
        </>
      ) : (
        <div
          className="tip-box"
          style={{ background: "#f5f5f4", border: "0.5px solid var(--border)", color: "var(--muted)" }}
        >
          {dim.status === "uncomputable" ? "⚠️ " : "ℹ️ "}
          {STATUS_META[dim.status].note}
          {dim.detail?.reason && (
            <>
              <br />
              <span style={{ fontSize: 12 }}>{dim.detail.reason}</span>
            </>
          )}
        </div>
      )}
    </div>
  );
}
