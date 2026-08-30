import { useState } from "react";

// Decorative hero illustration lifted verbatim from the original App.js
// during the file split. The landing-page redesign (step 6) replaces the
// hero entirely -- "No cards in the hero" -- so this is expected to be
// deleted then, not restyled.
export default function ResumeVisual() {
  const [magPos, setMagPos] = useState({ x: 180, y: 180 });
  const [isHovering, setIsHovering] = useState(false);
  const RESUME_LEFT = 60,
    RESUME_TOP = 40,
    RESUME_W = 260,
    RESUME_H = 360;
  const LENS = 130,
    SCALE = 2.8;
  const relX = Math.max(0, Math.min(1, (magPos.x - RESUME_LEFT) / RESUME_W));
  const relY = Math.max(0, Math.min(1, (magPos.y - RESUME_TOP) / RESUME_H));

  const resumeContent = (
    <div
      style={{
        width: RESUME_W,
        height: RESUME_H,
        background: "#fff",
        padding: "18px",
        position: "absolute",
        transform: `scale(${SCALE})`,
        transformOrigin: `${relX * 100}% ${relY * 100}%`,
        left: LENS / 2 - relX * RESUME_W * SCALE,
        top: LENS / 2 - relY * RESUME_H * SCALE,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
        <div>
          <p style={{ fontSize: 11, fontWeight: 700, color: "#6366f1", marginBottom: 2 }}>Anu Mishra</p>
          <p style={{ fontSize: 7.5, color: "#9ca3af" }}>Full Stack Developer · AI/ML Engineer</p>
          <p style={{ fontSize: 6.5, color: "#9ca3af" }}>anumishra@gmail.com · +91 9125812318</p>
        </div>
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: "50%",
            background: "linear-gradient(135deg,#6366f1,#8b5cf6)",
            flexShrink: 0,
          }}
        />
      </div>
      <div style={{ height: 1, background: "#f0f0ee", margin: "6px 0" }} />
      <p
        style={{
          fontSize: 6.5,
          fontWeight: 700,
          color: "#6366f1",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          marginBottom: 5,
        }}
      >
        Experience
      </p>
      <p style={{ fontSize: 7.5, fontWeight: 600, color: "#374151", marginBottom: 2 }}>
        Pinfinity Foundation — Full Stack Dev
      </p>
      <p style={{ fontSize: 6.5, color: "#6b7280", marginBottom: 1 }}>
        · Built scalable REST APIs · Improved speed by 30%
      </p>
      <p style={{ fontSize: 6.5, color: "#6b7280", marginBottom: 6 }}>
        · JWT Auth · MongoDB · Node.js · RBAC implemented
      </p>
      <div style={{ height: 1, background: "#f0f0ee", margin: "5px 0" }} />
      <p
        style={{
          fontSize: 6.5,
          fontWeight: 700,
          color: "#6366f1",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          marginBottom: 5,
        }}
      >
        Skills
      </p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 3, marginBottom: 6 }}>
        {["Python", "Node.js", "React", "FastAPI", "MongoDB", "JWT", "REST APIs", "ML", "Pandas"].map((t) => (
          <span
            key={t}
            style={{
              background: "#eef2ff",
              color: "#6366f1",
              fontSize: 6,
              padding: "2px 6px",
              borderRadius: 999,
              fontWeight: 500,
            }}
          >
            {t}
          </span>
        ))}
      </div>
      <div style={{ height: 1, background: "#f0f0ee", margin: "5px 0" }} />
      <p
        style={{
          fontSize: 6.5,
          fontWeight: 700,
          color: "#6366f1",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          marginBottom: 5,
        }}
      >
        Projects
      </p>
      <p style={{ fontSize: 7.5, fontWeight: 600, color: "#374151", marginBottom: 2 }}>
        CodeSense AI — Code Review Platform
      </p>
      <p style={{ fontSize: 6.5, color: "#6b7280", marginBottom: 1 }}>
        · AI-driven suggestions · 40% less review effort
      </p>
      <p style={{ fontSize: 7.5, fontWeight: 600, color: "#374151", marginBottom: 2, marginTop: 4 }}>
        PulseChat — Real-Time Messaging
      </p>
      <p style={{ fontSize: 6.5, color: "#6b7280", marginBottom: 6 }}>
        · Socket.IO · WebSockets · 35% lower latency
      </p>
      <div style={{ height: 1, background: "#f0f0ee", margin: "5px 0" }} />
      <p
        style={{
          fontSize: 6.5,
          fontWeight: 700,
          color: "#6366f1",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          marginBottom: 5,
        }}
      >
        Education
      </p>
      <p style={{ fontSize: 7.5, fontWeight: 600, color: "#374151", marginBottom: 2 }}>
        KNIT Sultanpur — B.Tech Electronics
      </p>
      <p style={{ fontSize: 6.5, color: "#6b7280" }}>CGPA: 8.8 / 10 · Expected 2027</p>
    </div>
  );

  return (
    <div
      style={{ position: "relative", width: 380, height: 480, cursor: "none", userSelect: "none" }}
      onMouseMove={(e) => {
        const r = e.currentTarget.getBoundingClientRect();
        setMagPos({ x: e.clientX - r.left, y: e.clientY - r.top });
        setIsHovering(true);
      }}
      onMouseLeave={() => setIsHovering(false)}
    >
      <div
        style={{
          position: "absolute",
          width: 180,
          height: 180,
          background: "#c7d2fe",
          borderRadius: "50%",
          filter: "blur(40px)",
          opacity: 0.4,
          top: 80,
          right: 10,
          zIndex: 0,
        }}
      />
      <div
        style={{
          position: "absolute",
          width: 140,
          height: 140,
          background: "#ddd6fe",
          borderRadius: "50%",
          filter: "blur(40px)",
          opacity: 0.4,
          bottom: 60,
          left: 10,
          zIndex: 0,
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 20,
          left: 80,
          width: 240,
          height: 360,
          background: "linear-gradient(135deg,#6366f1,#8b5cf6)",
          borderRadius: 16,
          animation: "float 5s ease-in-out infinite",
          zIndex: 0,
          boxShadow: "0 20px 60px rgba(99,102,241,0.3)",
        }}
      />
      <div
        style={{
          position: "absolute",
          top: RESUME_TOP,
          left: RESUME_LEFT,
          width: RESUME_W,
          height: RESUME_H,
          background: "#fff",
          borderRadius: 12,
          zIndex: 1,
          overflow: "hidden",
          boxShadow: "0 20px 60px rgba(0,0,0,0.15),0 4px 16px rgba(0,0,0,0.08)",
          border: "0.5px solid rgba(0,0,0,0.08)",
          padding: "18px",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
          <div>
            <div style={{ width: 52, height: 7, background: "#6366f1", borderRadius: 3, marginBottom: 4 }} />
            <div style={{ width: 80, height: 5, background: "#e0e7ff", borderRadius: 3, marginBottom: 3 }} />
            <div style={{ width: 64, height: 4, background: "#f0f0ee", borderRadius: 3 }} />
          </div>
          <div
            style={{
              width: 28,
              height: 28,
              borderRadius: "50%",
              background: "linear-gradient(135deg,#6366f1,#8b5cf6)",
              flexShrink: 0,
            }}
          />
        </div>
        <div style={{ height: 1, background: "#f0f0ee", margin: "6px 0" }} />
        <div
          style={{
            fontSize: 6,
            fontWeight: 700,
            color: "#6366f1",
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            marginBottom: 4,
          }}
        >
          Experience
        </div>
        {[100, 85, 70, 60].map((w, i) => (
          <div
            key={i}
            style={{
              width: `${w}%`,
              height: i === 0 ? 6 : 5,
              background: i === 0 ? "#e0e7ff" : "#f0f0ee",
              borderRadius: 3,
              marginBottom: 4,
            }}
          />
        ))}
        <div style={{ height: 1, background: "#f0f0ee", margin: "6px 0" }} />
        <div
          style={{
            fontSize: 6,
            fontWeight: 700,
            color: "#6366f1",
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            marginBottom: 4,
          }}
        >
          Skills
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 3, marginBottom: 6 }}>
          {[48, 36, 52, 40, 44, 38, 56, 42].map((w, i) => (
            <div
              key={i}
              style={{ width: w, height: 10, background: i % 2 === 0 ? "#eef2ff" : "#f0f0ee", borderRadius: 999 }}
            />
          ))}
        </div>
        <div style={{ height: 1, background: "#f0f0ee", margin: "6px 0" }} />
        <div
          style={{
            fontSize: 6,
            fontWeight: 700,
            color: "#6366f1",
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            marginBottom: 4,
          }}
        >
          Projects
        </div>
        {[100, 80, 100, 75].map((w, i) => (
          <div
            key={i}
            style={{
              width: `${w}%`,
              height: i % 2 === 0 ? 6 : 5,
              background: i % 2 === 0 ? "#e0e7ff" : "#f0f0ee",
              borderRadius: 3,
              marginBottom: 4,
            }}
          />
        ))}
        <div style={{ height: 1, background: "#f0f0ee", margin: "6px 0" }} />
        <div
          style={{
            fontSize: 6,
            fontWeight: 700,
            color: "#6366f1",
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            marginBottom: 4,
          }}
        >
          Education
        </div>
        {[90, 65].map((w, i) => (
          <div
            key={i}
            style={{
              width: `${w}%`,
              height: i === 0 ? 6 : 5,
              background: i === 0 ? "#e0e7ff" : "#f0f0ee",
              borderRadius: 3,
              marginBottom: 4,
            }}
          />
        ))}
      </div>
      <div
        style={{
          position: "absolute",
          top: 10,
          right: 10,
          zIndex: 3,
          background: "#6366f1",
          color: "#fff",
          padding: "8px 13px",
          borderRadius: 10,
          fontSize: 10,
          fontWeight: 600,
          boxShadow: "0 8px 24px rgba(99,102,241,0.3)",
          animation: "floatC 3.5s ease-in-out infinite",
        }}
      >
        ✦ AI Powered
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 70,
          right: 0,
          zIndex: 3,
          background: "#f0fdf4",
          color: "#16a34a",
          padding: "7px 12px",
          borderRadius: 10,
          fontSize: 10,
          fontWeight: 600,
          border: "0.5px solid #bbf7d0",
          boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
          animation: "floatB 4s ease-in-out infinite",
        }}
      >
        ✓ ATS Friendly
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 24,
          left: 10,
          zIndex: 3,
          background: "#fff",
          color: "#6b7280",
          padding: "7px 12px",
          borderRadius: 10,
          fontSize: 10,
          fontWeight: 500,
          border: "0.5px solid rgba(0,0,0,0.08)",
          boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
          animation: "float 5s ease-in-out infinite",
        }}
      >
        ⚡ Instant Analysis
      </div>
      <div
        style={{
          position: "absolute",
          left: magPos.x - LENS / 2,
          top: magPos.y - LENS / 2,
          zIndex: 10,
          opacity: isHovering ? 1 : 0,
          transition: "opacity 0.2s",
          pointerEvents: "none",
          filter: "drop-shadow(0 8px 24px rgba(0,0,0,0.2))",
        }}
      >
        <div
          style={{
            width: LENS,
            height: LENS,
            borderRadius: "50%",
            border: "3px solid rgba(255,255,255,0.95)",
            boxShadow: "0 8px 32px rgba(0,0,0,0.25),0 0 0 1px rgba(0,0,0,0.08)",
            overflow: "hidden",
            position: "relative",
            background: "#fff",
          }}
        >
          <div style={{ position: "absolute", inset: 0, borderRadius: "50%", overflow: "hidden" }}>{resumeContent}</div>
          <div
            style={{
              position: "absolute",
              top: 8,
              left: 14,
              width: 28,
              height: 10,
              background: "rgba(255,255,255,0.55)",
              borderRadius: 999,
              transform: "rotate(-30deg)",
              pointerEvents: "none",
              zIndex: 2,
            }}
          />
          <div
            style={{
              position: "absolute",
              inset: 0,
              borderRadius: "50%",
              background:
                "radial-gradient(circle at 40% 35%,rgba(255,255,255,0.15) 0%,rgba(99,102,241,0.04) 100%)",
              pointerEvents: "none",
              zIndex: 3,
            }}
          />
        </div>
        <div
          style={{
            width: 5,
            height: 52,
            background: "linear-gradient(180deg,#d1d5db,#9ca3af)",
            borderRadius: "0 0 4px 4px",
            margin: "0 auto",
            transform: "rotate(38deg) translateX(22px) translateY(-12px)",
            transformOrigin: "top center",
            boxShadow: "1px 2px 6px rgba(0,0,0,0.18)",
          }}
        />
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 4,
          left: "50%",
          transform: "translateX(-50%)",
          fontSize: 11,
          color: "#9ca3af",
          whiteSpace: "nowrap",
          opacity: isHovering ? 0 : 1,
          transition: "opacity 0.3s",
          pointerEvents: "none",
        }}
      >
        Move cursor over resume to explore ↑
      </div>
    </div>
  );
}
