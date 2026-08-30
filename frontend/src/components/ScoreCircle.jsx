import { scoreColor } from "@/lib/score";

export default function ScoreCircle({ score, size = 110 }) {
  const r = 44,
    c = 2 * Math.PI * r,
    offset = c - (score / 100) * c;
  return (
    <svg width={size} height={size} viewBox="0 0 100 100">
      <circle cx="50" cy="50" r={r} fill="none" stroke="#e8e8e6" strokeWidth="8" />
      <circle
        cx="50"
        cy="50"
        r={r}
        fill="none"
        stroke={scoreColor(score)}
        strokeWidth="8"
        strokeDasharray={c}
        strokeDashoffset={offset}
        strokeLinecap="round"
        style={{
          transform: "rotate(-90deg)",
          transformOrigin: "50% 50%",
          transition: "stroke-dashoffset 1.2s ease",
        }}
      />
      <text
        x="50"
        y="48"
        textAnchor="middle"
        style={{ fontSize: 16, fontWeight: 700, fill: scoreColor(score), fontFamily: "Inter,sans-serif" }}
      >
        {score}
      </text>
      <text x="50" y="61" textAnchor="middle" style={{ fontSize: 8, fill: "#9ca3af", fontFamily: "Inter,sans-serif" }}>
        /100
      </text>
    </svg>
  );
}
