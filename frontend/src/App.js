import { useState } from "react";
import axios from "axios";

const API = "http://127.0.0.1:8000/api/resume";

const css = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #f8f8f6; --surface: #ffffff; --border: rgba(0,0,0,0.08);
    --text: #1a1a1a; --muted: #6b7280; --hint: #9ca3af;
    --success: #16a34a; --success-bg: #f0fdf4;
    --danger: #dc2626; --danger-bg: #fef2f2;
    --warning: #d97706; --warning-bg: #fffbeb;
    --info: #2563eb; --info-bg: #eff6ff;
    --accent: #6366f1; --accent-light: #eef2ff;
  }
  body { background: var(--bg); color: var(--text); font-family: 'Inter', system-ui, sans-serif; }
  @keyframes fadeUp { from { opacity:0; transform:translateY(14px); } to { opacity:1; transform:translateY(0); } }
  @keyframes spin { to { transform: rotate(360deg); } }
  @keyframes float { 0%,100%{transform:translateY(0px) rotate(-2deg);} 50%{transform:translateY(-12px) rotate(2deg);} }
  @keyframes floatB { 0%,100%{transform:translateY(0px) rotate(3deg);} 50%{transform:translateY(-8px) rotate(-1deg);} }
  @keyframes floatC { 0%,100%{transform:translateY(0px);} 50%{transform:translateY(-10px);} }
  @keyframes shimmer { to { background-position: -200% 0; } }
  @keyframes checkIn { from{opacity:0;transform:scale(0.5);} to{opacity:1;transform:scale(1);} }
  .fu{animation:fadeUp 0.5s ease both;} .fu2{animation:fadeUp 0.5s 0.1s ease both;} .fu3{animation:fadeUp 0.5s 0.2s ease both;}

  /* NAV */
  .nav { position:fixed; top:0; left:0; right:0; z-index:100; background:rgba(248,248,246,0.9); backdrop-filter:blur(12px); border-bottom:0.5px solid var(--border); padding:0 48px; height:60px; display:flex; align-items:center; justify-content:space-between; }
  .nav-logo { font-size:20px; font-weight:700; letter-spacing:-0.03em; color:var(--text); display:flex; align-items:center; gap:8px; cursor:pointer; background:none; border:none; font-family:'Inter',sans-serif; }
  .nav-logo-dot { width:8px; height:8px; background:var(--accent); border-radius:50%; display:inline-block; }
  .nav-links { display:flex; align-items:center; gap:28px; }
  .nav-link { font-size:13px; color:var(--muted); cursor:pointer; transition:color 0.15s; background:none; border:none; font-family:'Inter',sans-serif; padding:0; }
  .nav-link:hover,.nav-link.active { color:var(--text); font-weight:500; }
  .nav-btn { font-size:13px; font-weight:500; color:#fff; background:var(--accent); padding:8px 18px; border-radius:8px; border:none; cursor:pointer; font-family:'Inter',sans-serif; transition:background 0.15s; }
  .nav-btn:hover { background:#4f46e5; }

  /* HERO */
  .hero-page { min-height:100vh; padding-top:60px; display:grid; grid-template-columns:1fr 1fr; }
  .hero-left { padding:80px 56px 80px 64px; display:flex; flex-direction:column; justify-content:center; border-right:0.5px solid var(--border); }
  .hero-right { display:flex; align-items:center; justify-content:center; padding:60px 48px; background:linear-gradient(135deg,#f0f0ff 0%,#f8f0ff 50%,#f0f8ff 100%); position:relative; overflow:hidden; }
  .ai-badge { display:inline-flex; align-items:center; gap:6px; background:var(--accent-light); color:var(--accent); font-size:11px; font-weight:600; padding:5px 14px; border-radius:999px; margin-bottom:24px; border:0.5px solid rgba(99,102,241,0.2); }
  .hero-title { font-size:clamp(32px,4vw,52px); font-weight:700; letter-spacing:-0.03em; line-height:1.12; margin-bottom:16px; }
  .hero-title span { color:var(--accent); }
  .hero-sub { font-size:15px; color:var(--muted); line-height:1.7; margin-bottom:36px; max-width:420px; }

  /* CARDS */
  .upload-card { background:var(--surface); border-radius:16px; padding:28px; border:0.5px solid var(--border); box-shadow:0 4px 24px rgba(0,0,0,0.06); }
  .field-label { font-size:11px; font-weight:600; letter-spacing:0.06em; text-transform:uppercase; color:var(--muted); margin-bottom:8px; display:block; }
  .drop-zone { border:1.5px dashed rgba(0,0,0,0.14); border-radius:12px; padding:28px 20px; text-align:center; cursor:pointer; transition:all 0.2s; position:relative; margin-bottom:18px; background:var(--bg); }
  .drop-zone:hover { border-color:var(--accent); background:var(--accent-light); }
  .drop-zone input { position:absolute; inset:0; opacity:0; cursor:pointer; width:100%; height:100%; }
  .drop-icon { font-size:28px; margin-bottom:8px; display:block; }
  .drop-text { font-size:13px; color:var(--muted); margin-bottom:3px; }
  .drop-hint { font-size:11px; color:var(--hint); }
  .file-ok { font-size:13px; color:var(--success); margin-top:6px; font-weight:500; }
  textarea { width:100%; background:var(--bg); border:0.5px solid rgba(0,0,0,0.1); border-radius:10px; padding:12px 14px; color:var(--text); font-size:13px; font-family:'Inter',sans-serif; resize:none; outline:none; transition:border 0.2s; line-height:1.6; }
  textarea:focus { border-color:var(--accent); }
  textarea::placeholder { color:var(--hint); }
  .btn { display:inline-flex; align-items:center; justify-content:center; gap:8px; width:100%; padding:13px 20px; border-radius:10px; border:none; font-size:14px; font-weight:600; font-family:'Inter',sans-serif; cursor:pointer; transition:all 0.2s; margin-top:14px; }
  .btn-primary { background:var(--accent); color:#fff; }
  .btn-primary:hover { background:#4f46e5; transform:translateY(-1px); box-shadow:0 4px 12px rgba(99,102,241,0.3); }
  .btn-primary:disabled { opacity:0.5; cursor:not-allowed; transform:none; box-shadow:none; }
  .btn-ghost { background:var(--surface); color:var(--muted); border:0.5px solid var(--border); }
  .btn-ghost:hover { color:var(--text); }
  .btn-success { background:var(--success); color:#fff; }
  .btn-success:hover { opacity:0.9; }
  .privacy { font-size:12px; color:var(--hint); text-align:center; margin-top:12px; }
  .error-msg { font-size:13px; color:var(--danger); margin-top:10px; padding:10px 14px; background:var(--danger-bg); border-radius:8px; }
  .spinner { width:15px; height:15px; border:1.5px solid rgba(255,255,255,0.4); border-top-color:#fff; border-radius:50%; animation:spin 0.6s linear infinite; }

  /* 3D SCENE */
  .scene { position:relative; width:360px; height:420px; }
  .card-3d { position:absolute; border-radius:16px; box-shadow:0 20px 60px rgba(0,0,0,0.12),0 4px 16px rgba(0,0,0,0.08); overflow:hidden; }
  .card-main { width:260px; height:340px; background:#fff; top:40px; left:50px; animation:floatC 4s ease-in-out infinite; border:0.5px solid rgba(0,0,0,0.08); padding:20px; display:flex; flex-direction:column; gap:10px; }
  .card-back { width:240px; height:320px; background:linear-gradient(135deg,#6366f1,#8b5cf6); top:20px; left:70px; animation:float 5s ease-in-out infinite; z-index:-1; }
  .card-side { width:180px; height:220px; background:#fff; top:120px; left:-10px; animation:floatB 4.5s ease-in-out infinite; border:0.5px solid rgba(0,0,0,0.08); padding:16px; display:flex; flex-direction:column; gap:8px; }
  .card-chip { position:absolute; border-radius:12px; box-shadow:0 8px 24px rgba(0,0,0,0.12); }
  .chip-score { background:var(--accent); color:#fff; padding:10px 16px; top:10px; right:10px; font-size:12px; font-weight:600; animation:floatC 3.5s ease-in-out infinite; }
  .chip-check { background:#f0fdf4; color:#16a34a; padding:8px 14px; bottom:60px; right:0; font-size:11px; font-weight:600; border:0.5px solid #bbf7d0; animation:floatB 4s ease-in-out infinite; }
  .chip-ai { background:#fff; color:var(--muted); padding:8px 14px; bottom:20px; left:10px; font-size:11px; font-weight:500; border:0.5px solid var(--border); animation:float 5s ease-in-out infinite; }
  .resume-line { background:#f0f0ee; border-radius:4px; height:8px; }
  .resume-line.short { width:60%; } .resume-line.med { width:80%; } .resume-line.full { width:100%; }
  .resume-section-label { font-size:8px; font-weight:700; color:var(--accent); text-transform:uppercase; letter-spacing:0.06em; }
  .scene-bg-blob { position:absolute; border-radius:50%; filter:blur(40px); opacity:0.4; z-index:0; }

  /* LOADING */
  .loading-page { min-height:100vh; display:grid; grid-template-columns:320px 1fr; padding-top:60px; }
  .loading-left { background:var(--surface); border-right:0.5px solid var(--border); padding:40px 24px; }
  .loading-right { padding:80px 64px; display:flex; align-items:flex-start; }
  .skeleton { background:linear-gradient(90deg,#f0f0ee 25%,#e8e8e6 50%,#f0f0ee 75%); background-size:200% 100%; animation:shimmer 1.5s infinite; border-radius:6px; height:10px; margin-bottom:8px; }
  .checklist { width:100%; max-width:440px; }
  .check-item { display:flex; align-items:center; gap:16px; padding:18px 0; border-bottom:0.5px solid var(--border); }
  .check-item:last-child { border-bottom:none; }
  .check-icon { width:30px; height:30px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:14px; flex-shrink:0; }
  .check-icon.done { background:var(--success-bg); color:var(--success); animation:checkIn 0.3s ease both; }
  .check-icon.active { background:var(--info-bg); }
  .check-icon.pending { background:#f5f5f4; }
  .check-label { font-size:16px; }
  .check-label.done { color:var(--text); font-weight:500; }
  .check-label.active { color:var(--text); font-weight:500; }
  .check-label.pending { color:var(--hint); }

  /* RESULTS */
  .results-page { min-height:100vh; display:grid; grid-template-columns:300px 1fr; padding-top:60px; }
  .results-left { background:var(--surface); border-right:0.5px solid var(--border); padding:28px 16px; position:sticky; top:60px; height:calc(100vh - 60px); overflow-y:auto; box-shadow:4px 0 20px rgba(0,0,0,0.04); }
  .results-right { padding:40px 48px; max-width:760px; }
  .score-box { background:linear-gradient(135deg,var(--accent-light),#f5f0ff); border-radius:14px; padding:24px 16px; text-align:center; margin-bottom:20px; border:0.5px solid rgba(99,102,241,0.15); }
  .score-box-label { font-size:13px; color:var(--muted); font-weight:500; margin-bottom:12px; }
  .score-box-num { font-size:64px; font-weight:700; letter-spacing:-0.04em; line-height:1; }
  .score-box-sub { font-size:12px; color:var(--muted); margin-top:8px; }
  .cat-item { display:flex; align-items:center; justify-content:space-between; padding:10px 12px; border-radius:10px; margin-bottom:3px; cursor:pointer; transition:all 0.15s; }
  .cat-item:hover { background:var(--bg); }
  .cat-item.active { background:var(--accent); color:white; }
  .cat-left { display:flex; align-items:center; gap:8px; font-size:13px; font-weight:500; }
  .cat-badge { font-size:11px; font-weight:600; padding:2px 8px; border-radius:999px; }
  .section-card { background:var(--surface); border-radius:16px; border:0.5px solid var(--border); padding:28px; margin-bottom:16px; animation:fadeUp 0.3s ease both; box-shadow:0 2px 12px rgba(0,0,0,0.04); }
  .section-card h2 { font-size:16px; font-weight:600; margin-bottom:6px; }
  .section-desc { font-size:13px; color:var(--muted); margin-bottom:18px; line-height:1.65; }
  .score-bar-track { background:#f0f0ee; border-radius:999px; height:6px; margin:12px 0 16px; overflow:hidden; }
  .score-bar-fill { height:100%; border-radius:999px; transition:width 1.2s cubic-bezier(0.4,0,0.2,1); }
  .tags { display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; }
  .tag { padding:4px 12px; border-radius:999px; font-size:12px; }
  .tag-success { background:var(--success-bg); color:var(--success); }
  .tag-danger { background:var(--danger-bg); color:var(--danger); }
  .tag-info { background:var(--info-bg); color:var(--info); }
  .check-row { display:flex; align-items:center; justify-content:space-between; padding:10px 0; border-bottom:0.5px solid var(--border); font-size:13px; }
  .check-row:last-child { border-bottom:none; }
  .mistake-item { background:var(--danger-bg); border-radius:8px; padding:12px 14px; margin-bottom:8px; }
  .mistake-word { font-weight:600; color:var(--danger); font-size:13px; }
  .mistake-suggestion { font-size:12px; color:var(--muted); margin-top:3px; }
  .tip-box { background:#fffbeb; border:0.5px solid #fcd34d; border-radius:10px; padding:14px; margin-top:16px; font-size:13px; color:#92400e; line-height:1.6; }
  .back-btn { display:flex; align-items:center; gap:6px; font-size:13px; color:var(--muted); cursor:pointer; margin-bottom:24px; transition:color 0.15s; background:none; border:none; font-family:'Inter',sans-serif; padding:0; }
  .back-btn:hover { color:var(--text); }

  /* COVER LETTER PAGE */
  .cl-page { min-height:100vh; padding-top:60px; display:grid; grid-template-columns:1fr 1fr; }
  .cl-left { padding:56px 48px 56px 64px; border-right:0.5px solid var(--border); overflow-y:auto; }
  .cl-right { padding:56px 48px; background:linear-gradient(135deg,#f0f0ff,#f8f0ff); display:flex; flex-direction:column; overflow-y:auto; min-height:100vh; }
  .cl-title { font-size:clamp(28px,3vw,42px); font-weight:700; letter-spacing:-0.03em; margin-bottom:10px; }
  .cl-sub { font-size:14px; color:var(--muted); margin-bottom:32px; line-height:1.65; }
  .tone-row { display:flex; gap:8px; margin-bottom:20px; flex-wrap:wrap; }
  .tone-btn { padding:7px 16px; border-radius:999px; border:0.5px solid var(--border); font-size:12px; font-weight:500; cursor:pointer; font-family:'Inter',sans-serif; background:var(--surface); color:var(--muted); transition:all 0.15s; }
  .tone-btn.active { background:var(--accent); color:#fff; border-color:var(--accent); }
.tone-btn.active:hover { background:#4f46e5; color:#fff; border-color:#4f46e5; }
.tone-btn:not(.active):hover { border-color:var(--accent); color:var(--accent); }
.cl-output { background:var(--surface); border-radius:16px; border:0.5px solid var(--border); padding:28px; flex:1; min-height:400px; position:relative; box-shadow:0 4px 24px rgba(0,0,0,0.06); overflow-y:auto; }  .cl-output-placeholder { display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; min-height:360px; text-align:center; gap:12px; }
  .cl-placeholder-icon { font-size:48px; opacity:0.3; }
  .cl-placeholder-text { font-size:14px; color:var(--hint); }
  .cl-letter { font-size:13px; line-height:1.9; color:var(--text); white-space:pre-wrap; }
  .cl-subject { background:var(--accent-light); border-radius:10px; padding:12px 16px; margin-bottom:20px; font-size:13px; font-weight:500; color:var(--accent); }
  .cl-subject span { color:var(--muted); font-weight:400; margin-right:6px; }
  .cl-points { margin-bottom:20px; }
  .cl-point { display:flex; gap:10px; font-size:13px; color:var(--muted); margin-bottom:8px; align-items:flex-start; }
  .cl-point-dot { width:6px; height:6px; background:var(--accent); border-radius:50%; margin-top:5px; flex-shrink:0; }
  .copy-btn { position:absolute; top:16px; right:16px; padding:6px 14px; border-radius:8px; border:0.5px solid var(--border); background:var(--bg); font-size:12px; font-weight:500; cursor:pointer; font-family:'Inter',sans-serif; color:var(--muted); transition:all 0.15s; }
  .copy-btn:hover { color:var(--text); border-color:var(--accent); }
  .cl-loading { display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; min-height:360px; gap:16px; }
  .cl-spinner { width:32px; height:32px; border:2.5px solid var(--accent-light); border-top-color:var(--accent); border-radius:50%; animation:spin 0.8s linear infinite; }
  .cl-loading-text { font-size:14px; color:var(--muted); }

  /* HOW IT WORKS */
  .hiw-page { min-height:100vh; padding:100px 64px 80px; max-width:900px; margin:0 auto; }
  .hiw-title { font-size:clamp(32px,5vw,48px); font-weight:700; letter-spacing:-0.03em; margin-bottom:12px; text-align:center; }
  .hiw-title span { color:var(--accent); }
  .hiw-sub { font-size:15px; color:var(--muted); text-align:center; margin-bottom:72px; line-height:1.7; }
  .hiw-steps { display:flex; flex-direction:column; gap:0; }
  .hiw-step { display:grid; grid-template-columns:80px 1fr; gap:32px; position:relative; padding-bottom:48px; }
  .hiw-step:last-child { padding-bottom:0; }
  .hiw-step-left { display:flex; flex-direction:column; align-items:center; }
  .hiw-num { width:48px; height:48px; border-radius:50%; background:var(--accent); color:#fff; display:flex; align-items:center; justify-content:center; font-size:16px; font-weight:700; flex-shrink:0; z-index:1; }
  .hiw-line { width:2px; background:linear-gradient(180deg,var(--accent),var(--accent-light)); flex:1; margin-top:8px; border-radius:999px; }
  .hiw-step:last-child .hiw-line { display:none; }
  .hiw-content { padding-top:10px; }
  .hiw-step-title { font-size:18px; font-weight:600; margin-bottom:8px; }
  .hiw-step-desc { font-size:14px; color:var(--muted); line-height:1.7; margin-bottom:16px; }
  .hiw-step-card { background:var(--surface); border-radius:14px; border:0.5px solid var(--border); padding:18px 20px; box-shadow:0 2px 12px rgba(0,0,0,0.04); }
  .hiw-step-card-row { display:flex; align-items:center; gap:10px; font-size:13px; color:var(--muted); padding:6px 0; border-bottom:0.5px solid var(--border); }
  .hiw-step-card-row:last-child { border-bottom:none; }
  .hiw-icon { font-size:16px; }

  @media (max-width:900px) {
    .hero-page,.cl-page { grid-template-columns:1fr; }
    .hero-right { display:none; }
    .hero-left,.cl-left { padding:60px 24px; }
    .results-page,.loading-page { grid-template-columns:1fr; }
    .results-left { position:static; height:auto; }
    .results-right { padding:24px 20px; }
    .nav { padding:0 20px; }
    .nav-links { gap:16px; }
    .hiw-page { padding:80px 24px 60px; }
  }
`;

const LOAD_STEPS = ["Parsing your resume","Analyzing your experience","Extracting your skills","Generating recommendations"];

function scoreColor(s) {
  return s >= 80 ? "#16a34a" : s >= 60 ? "#d97706" : s >= 40 ? "#f97316" : "#dc2626";
}

function ScoreCircle({ score, size=110 }) {
  const r=44, c=2*Math.PI*r, offset=c-(score/100)*c;
  return (
    <svg width={size} height={size} viewBox="0 0 100 100">
      <circle cx="50" cy="50" r={r} fill="none" stroke="#e8e8e6" strokeWidth="8"/>
      <circle cx="50" cy="50" r={r} fill="none" stroke={scoreColor(score)} strokeWidth="8"
        strokeDasharray={c} strokeDashoffset={offset} strokeLinecap="round"
        style={{transform:"rotate(-90deg)",transformOrigin:"50% 50%",transition:"stroke-dashoffset 1.2s ease"}}/>
      <text x="50" y="48" textAnchor="middle" style={{fontSize:16,fontWeight:700,fill:scoreColor(score),fontFamily:"Inter,sans-serif"}}>{score}</text>
      <text x="50" y="61" textAnchor="middle" style={{fontSize:8,fill:"#9ca3af",fontFamily:"Inter,sans-serif"}}>/100</text>
    </svg>
  );
}
function ResumeVisual() {
  const [magPos, setMagPos] = useState({ x: 180, y: 180 });
  const [isHovering, setIsHovering] = useState(false);

  const handleMouseMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setMagPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    setIsHovering(true);
  };

  const RESUME_LEFT = 60, RESUME_TOP = 40, RESUME_W = 260, RESUME_H = 360;
  const LENS = 130, SCALE = 2.8;
  const relX = Math.max(0, Math.min(1, (magPos.x - RESUME_LEFT) / RESUME_W));
  const relY = Math.max(0, Math.min(1, (magPos.y - RESUME_TOP) / RESUME_H));

  const resumeContent = (
    <div style={{
      width: RESUME_W, height: RESUME_H,
      background: "#fff", padding: "18px",
      position: "absolute",
      transform: `scale(${SCALE})`,
      transformOrigin: `${relX * 100}% ${relY * 100}%`,
      left: LENS/2 - relX * RESUME_W * SCALE,
      top: LENS/2 - relY * RESUME_H * SCALE,
    }}>
      {/* Header */}
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:10}}>
        <div>
          <p style={{fontSize:11,fontWeight:700,color:"#6366f1",marginBottom:2}}>Anu Mishra</p>
          <p style={{fontSize:7.5,color:"#9ca3af"}}>Full Stack Developer · AI/ML Engineer</p>
          <p style={{fontSize:6.5,color:"#9ca3af"}}>anumishra@gmail.com · +91 9125812318</p>
        </div>
        <div style={{width:28,height:28,borderRadius:"50%",background:"linear-gradient(135deg,#6366f1,#8b5cf6)",flexShrink:0}}/>
      </div>
      <div style={{height:1,background:"#f0f0ee",margin:"6px 0"}}/>

      {/* Experience */}
      <p style={{fontSize:6.5,fontWeight:700,color:"#6366f1",textTransform:"uppercase",letterSpacing:"0.06em",marginBottom:5}}>Experience</p>
      <p style={{fontSize:7.5,fontWeight:600,color:"#374151",marginBottom:2}}>Pinfinity Foundation — Full Stack Dev</p>
      <p style={{fontSize:6.5,color:"#6b7280",marginBottom:1}}>· Built scalable REST APIs · Improved speed by 30%</p>
      <p style={{fontSize:6.5,color:"#6b7280",marginBottom:1}}>· JWT Auth · MongoDB · Node.js · Express.js</p>
      <p style={{fontSize:6.5,color:"#6b7280",marginBottom:6}}>· Reduced dev cycles by 25% · RBAC implemented</p>
      <div style={{height:1,background:"#f0f0ee",margin:"5px 0"}}/>

      {/* Skills */}
      <p style={{fontSize:6.5,fontWeight:700,color:"#6366f1",textTransform:"uppercase",letterSpacing:"0.06em",marginBottom:5}}>Skills</p>
      <div style={{display:"flex",flexWrap:"wrap",gap:3,marginBottom:6}}>
        {["Python","Node.js","React","FastAPI","MongoDB","JWT","REST APIs","ML","Pandas"].map(t=>(
          <span key={t} style={{background:"#eef2ff",color:"#6366f1",fontSize:6,padding:"2px 6px",borderRadius:999,fontWeight:500}}>{t}</span>
        ))}
      </div>
      <div style={{height:1,background:"#f0f0ee",margin:"5px 0"}}/>

      {/* Projects */}
      <p style={{fontSize:6.5,fontWeight:700,color:"#6366f1",textTransform:"uppercase",letterSpacing:"0.06em",marginBottom:5}}>Projects</p>
      <p style={{fontSize:7.5,fontWeight:600,color:"#374151",marginBottom:2}}>CodeSense AI — Code Review Platform</p>
      <p style={{fontSize:6.5,color:"#6b7280",marginBottom:1}}>· AI-driven suggestions · 40% less review effort</p>
      <p style={{fontSize:7.5,fontWeight:600,color:"#374151",marginBottom:2,marginTop:4}}>PulseChat — Real-Time Messaging</p>
      <p style={{fontSize:6.5,color:"#6b7280",marginBottom:6}}>· Socket.IO · WebSockets · 35% lower latency</p>
      <div style={{height:1,background:"#f0f0ee",margin:"5px 0"}}/>

      {/* Education */}
      <p style={{fontSize:6.5,fontWeight:700,color:"#6366f1",textTransform:"uppercase",letterSpacing:"0.06em",marginBottom:5}}>Education</p>
      <p style={{fontSize:7.5,fontWeight:600,color:"#374151",marginBottom:2}}>KNIT Sultanpur — B.Tech Electronics</p>
      <p style={{fontSize:6.5,color:"#6b7280"}}>CGPA: 8.8 / 10 · Expected 2027</p>
    </div>
  );

  return (
    <div
      style={{position:"relative",width:380,height:480,cursor:"none",userSelect:"none"}}
      onMouseMove={handleMouseMove}
      onMouseLeave={()=>setIsHovering(false)}
    >
      {/* Background blobs */}
      <div style={{position:"absolute",width:180,height:180,background:"#c7d2fe",borderRadius:"50%",filter:"blur(40px)",opacity:0.4,top:80,right:10,zIndex:0}}/>
      <div style={{position:"absolute",width:140,height:140,background:"#ddd6fe",borderRadius:"50%",filter:"blur(40px)",opacity:0.4,bottom:60,left:10,zIndex:0}}/>

      {/* Purple shadow card behind */}
      <div style={{
        position:"absolute",top:20,left:80,width:240,height:360,
        background:"linear-gradient(135deg,#6366f1,#8b5cf6)",
        borderRadius:16,animation:"float 5s ease-in-out infinite",zIndex:0,
        boxShadow:"0 20px 60px rgba(99,102,241,0.3)"
      }}/>

      {/* Resume paper — real content */}
      <div style={{
        position:"absolute",top:RESUME_TOP,left:RESUME_LEFT,
        width:RESUME_W,height:RESUME_H,
        background:"#fff",borderRadius:12,zIndex:1,overflow:"hidden",
        boxShadow:"0 20px 60px rgba(0,0,0,0.15),0 4px 16px rgba(0,0,0,0.08)",
        border:"0.5px solid rgba(0,0,0,0.08)",padding:"18px",
      }}>
        {/* Header */}
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:8}}>
          <div>
            <div style={{width:52,height:7,background:"#6366f1",borderRadius:3,marginBottom:4}}/>
            <div style={{width:80,height:5,background:"#e0e7ff",borderRadius:3,marginBottom:3}}/>
            <div style={{width:64,height:4,background:"#f0f0ee",borderRadius:3}}/>
          </div>
          <div style={{width:28,height:28,borderRadius:"50%",background:"linear-gradient(135deg,#6366f1,#8b5cf6)",flexShrink:0}}/>
        </div>
        <div style={{height:1,background:"#f0f0ee",margin:"6px 0"}}/>
        <div style={{fontSize:6,fontWeight:700,color:"#6366f1",textTransform:"uppercase",letterSpacing:"0.06em",marginBottom:4}}>Experience</div>
        {[100,85,70,60].map((w,i)=><div key={i} style={{width:`${w}%`,height:i===0?6:5,background:i===0?"#e0e7ff":"#f0f0ee",borderRadius:3,marginBottom:4}}/>)}
        <div style={{height:1,background:"#f0f0ee",margin:"6px 0"}}/>
        <div style={{fontSize:6,fontWeight:700,color:"#6366f1",textTransform:"uppercase",letterSpacing:"0.06em",marginBottom:4}}>Skills</div>
        <div style={{display:"flex",flexWrap:"wrap",gap:3,marginBottom:6}}>
          {[48,36,52,40,44,38,56,42].map((w,i)=><div key={i} style={{width:w,height:10,background:i%2===0?"#eef2ff":"#f0f0ee",borderRadius:999}}/>)}
        </div>
        <div style={{height:1,background:"#f0f0ee",margin:"6px 0"}}/>
        <div style={{fontSize:6,fontWeight:700,color:"#6366f1",textTransform:"uppercase",letterSpacing:"0.06em",marginBottom:4}}>Projects</div>
        {[100,80,100,75].map((w,i)=><div key={i} style={{width:`${w}%`,height:i%2===0?6:5,background:i%2===0?"#e0e7ff":"#f0f0ee",borderRadius:3,marginBottom:4}}/>)}
        <div style={{height:1,background:"#f0f0ee",margin:"6px 0"}}/>
        <div style={{fontSize:6,fontWeight:700,color:"#6366f1",textTransform:"uppercase",letterSpacing:"0.06em",marginBottom:4}}>Education</div>
        {[90,65].map((w,i)=><div key={i} style={{width:`${w}%`,height:i===0?6:5,background:i===0?"#e0e7ff":"#f0f0ee",borderRadius:3,marginBottom:4}}/>)}
      </div>

      {/* Floating chips */}
      <div style={{position:"absolute",top:10,right:10,zIndex:3,background:"#6366f1",color:"#fff",padding:"8px 13px",borderRadius:10,fontSize:10,fontWeight:600,boxShadow:"0 8px 24px rgba(99,102,241,0.3)",animation:"floatC 3.5s ease-in-out infinite"}}>✦ AI Powered</div>
      <div style={{position:"absolute",bottom:70,right:0,zIndex:3,background:"#f0fdf4",color:"#16a34a",padding:"7px 12px",borderRadius:10,fontSize:10,fontWeight:600,border:"0.5px solid #bbf7d0",boxShadow:"0 4px 12px rgba(0,0,0,0.08)",animation:"floatB 4s ease-in-out infinite"}}>✓ ATS Friendly</div>
      <div style={{position:"absolute",bottom:24,left:10,zIndex:3,background:"#fff",color:"#6b7280",padding:"7px 12px",borderRadius:10,fontSize:10,fontWeight:500,border:"0.5px solid rgba(0,0,0,0.08)",boxShadow:"0 4px 12px rgba(0,0,0,0.08)",animation:"float 5s ease-in-out infinite"}}>⚡ Instant Analysis</div>

      {/* MAGNIFYING GLASS */}
      <div style={{
        position:"absolute",
        left: magPos.x - LENS/2,
        top: magPos.y - LENS/2,
        zIndex:10,
        opacity: isHovering ? 1 : 0,
        transition:"opacity 0.2s",
        pointerEvents:"none",
        filter:"drop-shadow(0 8px 24px rgba(0,0,0,0.2))",
      }}>
        {/* Lens circle */}
        <div style={{
          width:LENS, height:LENS, borderRadius:"50%",
          border:"3px solid rgba(255,255,255,0.95)",
          boxShadow:"0 8px 32px rgba(0,0,0,0.25),0 0 0 1px rgba(0,0,0,0.08)",
          overflow:"hidden", position:"relative", background:"#fff",
        }}>
          {/* Zoomed content */}
          <div style={{position:"absolute",inset:0,borderRadius:"50%",overflow:"hidden"}}>
            {resumeContent}
          </div>

          {/* Glass shine */}
          <div style={{
            position:"absolute",top:8,left:14,width:28,height:10,
            background:"rgba(255,255,255,0.55)",borderRadius:999,
            transform:"rotate(-30deg)",pointerEvents:"none",zIndex:2
          }}/>

          {/* Subtle tint overlay */}
          <div style={{
            position:"absolute",inset:0,borderRadius:"50%",
            background:"radial-gradient(circle at 40% 35%,rgba(255,255,255,0.15) 0%,rgba(99,102,241,0.04) 100%)",
            pointerEvents:"none",zIndex:3
          }}/>
        </div>

        {/* Handle */}
        <div style={{
          width:5,height:52,
          background:"linear-gradient(180deg,#d1d5db,#9ca3af)",
          borderRadius:"0 0 4px 4px",
          margin:"0 auto",
          transform:"rotate(38deg) translateX(22px) translateY(-12px)",
          transformOrigin:"top center",
          boxShadow:"1px 2px 6px rgba(0,0,0,0.18)",
        }}/>
      </div>

      {/* Hint */}
      <div style={{
        position:"absolute",bottom:4,left:"50%",transform:"translateX(-50%)",
        fontSize:11,color:"#9ca3af",whiteSpace:"nowrap",
        opacity: isHovering ? 0 : 1, transition:"opacity 0.3s",
        pointerEvents:"none",
      }}>
        Move cursor over resume to explore ↑
      </div>
    </div>
  );
}

const CATEGORIES = [
  {key:"ats_match",label:"ATS Match",icon:"🎯"},
  {key:"quantification",label:"Quantify Impact",icon:"📊"},
  {key:"repetition",label:"Repetition",icon:"🔁"},
  {key:"contact",label:"Contact Info",icon:"📬"},
  {key:"file_format",label:"File Format & Size",icon:"📄"},
  {key:"sections",label:"Sections",icon:"📋"},
  {key:"grammar",label:"Spelling & Grammar",icon:"✍️"},
];

function CategoryBadge({score}) {
  const color=score>=80?"#16a34a":score>=60?"#d97706":"#dc2626";
  const bg=score>=80?"#f0fdf4":score>=60?"#fffbeb":"#fef2f2";
  return <span className="cat-badge" style={{background:bg,color}}>{score}%</span>;
}

function ATSSection({data}) {
  return <div className="section-card">
    <h2>🎯 ATS Match Score</h2>
    <p className="section-desc">How well your resume matches the job description based on skill keywords and terminology.</p>
    <div className="score-bar-track"><div className="score-bar-fill" style={{width:`${data.score}%`,background:scoreColor(data.score)}}/></div>
    <p style={{fontSize:13,color:"var(--muted)",marginBottom:14}}>{data.verdict}</p>
    {data.matched?.length>0&&<><p style={{fontSize:12,fontWeight:600,color:"var(--success)",marginBottom:6}}>✓ Matched Skills</p><div className="tags">{data.matched.map(s=><span key={s} className="tag tag-success">{s}</span>)}</div></>}
    {data.missing?.length>0&&<><p style={{fontSize:12,fontWeight:600,color:"var(--danger)",margin:"14px 0 6px"}}>✕ Missing Skills</p><div className="tags">{data.missing.map(s=><span key={s} className="tag tag-danger">{s}</span>)}</div></>}
    <div className="tip-box">💡 {data.tip}</div>
  </div>;
}

function QuantifySection({data}) {
  return <div className="section-card">
    <h2>📊 Quantify Impact</h2>
    <p className="section-desc">Bullet points with numbers and metrics are 40% more likely to get past ATS.</p>
    <div className="score-bar-track"><div className="score-bar-fill" style={{width:`${data.score}%`,background:scoreColor(data.score)}}/></div>
    <div className="check-row"><span>Total bullet points</span><strong>{data.total_bullets}</strong></div>
    <div className="check-row"><span>Quantified</span><strong style={{color:"var(--success)"}}>{data.quantified}</strong></div>
    <div className="check-row"><span>Missing numbers</span><strong style={{color:data.issues>0?"var(--danger)":"var(--success)"}}>{data.issues}</strong></div>
    <div className="tip-box">💡 {data.tip}</div>
  </div>;
}

function RepetitionSection({data}) {
  return <div className="section-card">
    <h2>🔁 Repetition</h2>
    <p className="section-desc">Vary your language to show range and avoid monotony.</p>
    <div className="score-bar-track"><div className="score-bar-fill" style={{width:`${data.score}%`,background:scoreColor(data.score)}}/></div>
    {data.repeated_words?.length>0?data.repeated_words.map((w,i)=><div key={i} className="check-row"><span style={{fontWeight:500}}>"{w.word}"</span><span style={{color:"var(--danger)",fontSize:12}}>used {w.count}×</span></div>):<p style={{color:"var(--success)",fontSize:13,marginTop:12}}>✓ No repetition issues found</p>}
    <div className="tip-box">💡 {data.tip}</div>
  </div>;
}

function ContactSection({data}) {
  return <div className="section-card">
    <h2>📬 Contact Information</h2>
    <p className="section-desc">Complete contact info ensures recruiters can reach you.</p>
    <div className="score-bar-track"><div className="score-bar-fill" style={{width:`${data.score}%`,background:scoreColor(data.score)}}/></div>
    {[["Email address",data.email],["Phone number",data.phone],["LinkedIn",data.linkedin],["GitHub",data.github]].map(([l,ok])=><div key={l} className="check-row"><span>{l}</span><span style={{color:ok?"var(--success)":"var(--danger)",fontWeight:600,fontSize:13}}>{ok?"✓ Found":"✕ Missing"}</span></div>)}
    <div className="tip-box">💡 {data.tip}</div>
  </div>;
}

function FileSection({data}) {
  return <div className="section-card">
    <h2>📄 File Format & Size</h2>
    <p className="section-desc">PDF files under 2MB are preferred by ATS systems.</p>
    <div className="score-bar-track"><div className="score-bar-fill" style={{width:`${data.score}%`,background:scoreColor(data.score)}}/></div>
    <div className="check-row"><span>Format</span><span style={{color:data.is_pdf?"var(--success)":"var(--danger)",fontWeight:600,fontSize:13}}>{data.is_pdf?"✓ PDF":"✕ Not PDF"}</span></div>
    <div className="check-row"><span>Size</span><span style={{color:data.size_ok?"var(--success)":"var(--danger)",fontWeight:600,fontSize:13}}>{data.size_ok?`✓ ${data.size_mb}MB`:`✕ ${data.size_mb}MB`}</span></div>
    <div className="tip-box">💡 {data.tip}</div>
  </div>;
}

function SectionsSection({data}) {
  return <div className="section-card">
    <h2>📋 Resume Sections</h2>
    <p className="section-desc">All key sections should be present for ATS and recruiters.</p>
    <div className="score-bar-track"><div className="score-bar-fill" style={{width:`${data.score}%`,background:scoreColor(data.score)}}/></div>
    {data.sections&&Object.entries(data.sections).map(([n,ok])=><div key={n} className="check-row"><span>{n}</span><span style={{color:ok?"var(--success)":"var(--danger)",fontWeight:600,fontSize:13}}>{ok?"✓ Found":"✕ Missing"}</span></div>)}
    <div className="tip-box">💡 {data.tip}</div>
  </div>;
}

function GrammarSection({data}) {
  return <div className="section-card">
    <h2>✍️ Spelling & Grammar</h2>
    <p className="section-desc">Even one spelling mistake can cost you the interview.</p>
    <div className="score-bar-track"><div className="score-bar-fill" style={{width:`${data.score}%`,background:scoreColor(data.score)}}/></div>
    {data.mistakes?.length>0?data.mistakes.map((m,i)=><div key={i} className="mistake-item"><p className="mistake-word">"{m.word}" → {m.suggestion}</p>{m.context&&<p className="mistake-suggestion">{m.context}</p>}</div>):<p style={{color:"var(--success)",fontSize:13,marginTop:12}}>✓ No issues found</p>}
    <div className="tip-box">💡 {data.tip}</div>
  </div>;
}

function CoverLetterPage({ onBack }) {
  const [file, setFile] = useState(null);
  const [jd, setJd] = useState("");
  const [tone, setTone] = useState("professional");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  const tones = ["professional","friendly","confident","creative","concise"];

  const handleGenerate = async () => {
  if (!file) return setError("Please upload your resume PDF");
  if (!jd.trim()) return setError("Please paste a job description");
  setLoading(true); setError(""); setResult(null);
  try {
    const form = new FormData();
    form.append("file", file);
    const r1 = await axios.post(`${API}/upload`, form);
    const text = r1.data.full_text;
    if (!text || text.length < 10) {
      setError("Could not extract text from PDF.");
      setLoading(false);
      return;
    }
    const r2 = await axios.post(`${API}/cover-letter`, {
      resume_text: text,
      job_description: jd,
      tone: tone,
    });
    if (r2.data && r2.data.cover_letter) {
      setResult(r2.data);
    } else {
      setError("Generation failed. Please try again.");
    }
  } catch(e) {
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
      {/* Left */}
      <div className="cl-left fu">
        <button className="back-btn" onClick={onBack}>← Back to home</button>
        <div className="ai-badge">✦ AI Cover Letter Generator</div>
        <h1 className="cl-title">Generate your<br /><span style={{color:"var(--accent)"}}>cover letter</span></h1>
        <p className="cl-sub">Upload your resume and paste the job description. Our AI will write a tailored, compelling cover letter in seconds.</p>

        <div className="upload-card">
          <label className="field-label">Resume (PDF)</label>
          <div className="drop-zone" style={{marginBottom:18}}>
            <input type="file" accept=".pdf" onChange={e=>{setFile(e.target.files[0]);setResult(null);}}/>
            <span className="drop-icon">📄</span>
            <p className="drop-text">{file?"":"Click to upload your resume"}</p>
            <p className="drop-hint">{file?"":"PDF only"}</p>
            {file&&<p className="file-ok">✓ {file.name}</p>}
          </div>

          <label className="field-label">Job Description</label>
          <textarea rows={5} value={jd} onChange={e=>setJd(e.target.value)}
            placeholder="Paste the job description here..." style={{marginBottom:18}}/>

          <label className="field-label">Tone</label>
          <div className="tone-row">
            {tones.map(t=>(
              <button key={t} className={`tone-btn ${tone===t?"active":""}`} onClick={()=>setTone(t)}>
                {t.charAt(0).toUpperCase()+t.slice(1)}
              </button>
            ))}
          </div>

          {error&&<div className="error-msg">{error}</div>}
          <button className="btn btn-primary" onClick={handleGenerate} disabled={loading}>
            {loading?<><div className="spinner"/>Generating...</>:"Generate Cover Letter →"}
          </button>
          <p className="privacy">🔒 Your data is never stored</p>
        </div>
      </div>

      {/* Right — output */}
      <div className="cl-right fu2">
        <h2 style={{fontSize:16,fontWeight:600,marginBottom:20,color:"var(--text)"}}>Your Cover Letter</h2>
        <div className="cl-output">
          {loading && (
            <div className="cl-loading">
              <div className="cl-spinner"/>
              <p className="cl-loading-text">Writing your cover letter with AI...</p>
            </div>
          )}
          {!loading && !result && (
            <div className="cl-output-placeholder">
              <div className="cl-placeholder-icon">✉️</div>
              <p className="cl-placeholder-text">Your AI-generated cover letter<br/>will appear here</p>
            </div>
          )}
          {!loading && result && (
            <>
              <button className="copy-btn" onClick={handleCopy}>{copied?"✓ Copied!":"Copy"}</button>
              {result.subject_line&&(
                <div className="cl-subject">
                  <span>Subject:</span>{result.subject_line}
                </div>
              )}
              {result.key_points?.length>0&&(
                <div className="cl-points">
                  <p style={{fontSize:11,fontWeight:600,color:"var(--hint)",textTransform:"uppercase",letterSpacing:"0.06em",marginBottom:8}}>Key highlights</p>
                  {result.key_points.map((p,i)=>(
                    <div key={i} className="cl-point">
                      <div className="cl-point-dot"/>
                      <span>{p}</span>
                    </div>
                  ))}
                </div>
              )}
              <div style={{height:1,background:"var(--border)",marginBottom:20}}/>
              <p className="cl-letter">{result.cover_letter}</p>
              <div style={{marginTop:20,paddingTop:16,borderTop:"0.5px solid var(--border)"}}>
                <p style={{fontSize:12,color:"var(--hint)"}}>~{result.word_count} words · {tone} tone</p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function HowItWorksPage({ onBack }) {
  const steps = [
    {
      num:"01", title:"Upload your resume",
      desc:"Drag and drop your PDF resume into the analyzer. Our system instantly extracts and parses all content — work experience, skills, education, and contact info.",
      card:[
        {icon:"📄", text:"PDF format supported"},
        {icon:"⚡", text:"Instant text extraction"},
        {icon:"🔒", text:"Your data is never stored"},
      ]
    },
    {
      num:"02", title:"Paste the job description",
      desc:"Copy the full job description from LinkedIn, Indeed, or any job board and paste it in. The more detailed the JD, the more accurate your ATS score will be.",
      card:[
        {icon:"🎯", text:"Keyword extraction from JD"},
        {icon:"🔍", text:"Skill gap identification"},
        {icon:"📊", text:"Match percentage calculated"},
      ]
    },
    {
      num:"03", title:"AI analyzes your resume",
      desc:"Our AI runs 7 crucial checks — ATS score, quantified impact, repetition, contact info, file format, section completeness, and spelling & grammar.",
      card:[
        {icon:"🤖", text:"Powered by Google Gemini AI"},
        {icon:"✅", text:"7 checks in under 10 seconds"},
        {icon:"📈", text:"Weighted overall score generated"},
      ]
    },
    {
      num:"04", title:"Review detailed results",
      desc:"Get a full breakdown of every check with specific issues found, your score per category, and actionable tips to fix each problem.",
      card:[
        {icon:"📋", text:"Category-by-category breakdown"},
        {icon:"💡", text:"Specific improvement tips"},
        {icon:"🏆", text:"Overall score out of 100"},
      ]
    },
    {
      num:"05", title:"Generate cover letter",
      desc:"Use the Cover Letter Generator to create a tailored, professional cover letter based on your resume and the job description — in your chosen tone.",
      card:[
        {icon:"✉️", text:"AI-written in seconds"},
        {icon:"🎨", text:"5 tone options to choose from"},
        {icon:"📋", text:"One-click copy to clipboard"},
      ]
    },
    {
      num:"06", title:"Apply with confidence",
      desc:"With an optimized resume and a polished cover letter, you're ready to apply. Track your improvements by re-analyzing after making changes.",
      card:[
        {icon:"🚀", text:"ATS-optimized resume"},
        {icon:"📩", text:"Tailored cover letter ready"},
        {icon:"🎯", text:"Higher interview callback rate"},
      ]
    },
  ];

  return (
    <div className="hiw-page fu">
      <button className="back-btn" onClick={onBack} style={{marginBottom:40}}>← Back to home</button>
      <div style={{textAlign:"center",marginBottom:64}}>
        <div className="ai-badge" style={{marginBottom:20}}>How it works</div>
        <h1 className="hiw-title">From upload to <span>offer letter</span></h1>
        <p className="hiw-sub">6 simple steps to get your resume ATS-ready and land more interviews</p>
      </div>
      <div className="hiw-steps">
        {steps.map((step,i)=>(
          <div key={i} className="hiw-step fu" style={{animationDelay:`${i*0.08}s`}}>
            <div className="hiw-step-left">
              <div className="hiw-num">{step.num}</div>
              <div className="hiw-line"/>
            </div>
            <div className="hiw-content">
              <h3 className="hiw-step-title">{step.title}</h3>
              <p className="hiw-step-desc">{step.desc}</p>
              <div className="hiw-step-card">
                {step.card.map((row,j)=>(
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

export default function App() {
  const [page, setPage] = useState("home");
  const [subPage, setSubPage] = useState("upload");
  const [file, setFile] = useState(null);
  const [jd, setJd] = useState("");
  const [loadStep, setLoadStep] = useState(0);
  const [analysis, setAnalysis] = useState(null);
  const [activeCategory, setActiveCategory] = useState("ats_match");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleAnalyze = async () => {
    if (!file) return setError("Please upload a PDF resume");
    if (!jd.trim()) return setError("Please paste a job description");
    setLoading(true); setError(""); setSubPage("loading"); setLoadStep(0);
    try {
      const form = new FormData();
      form.append("file", file);
      setLoadStep(1);
      const r1 = await axios.post(`${API}/upload`, form);
      const text = r1.data.full_text;
      setLoadStep(2);
      await new Promise(r=>setTimeout(r,700));
      setLoadStep(3);
      await new Promise(r=>setTimeout(r,700));
      setLoadStep(4);
      const r2 = await axios.post(`${API}/analyze`,{
        resume_text:text, job_description:jd,
        filename:file.name, file_size:file.size,
      });
      setAnalysis(r2.data);
      setSubPage("results");
    } catch {
      setError("Something went wrong. Make sure backend is running.");
      setSubPage("upload");
    }
    setLoading(false);
  };

  const reset = () => {
    setSubPage("upload"); setAnalysis(null); setFile(null);
    setJd(""); setError(""); setLoadStep(0); setActiveCategory("ats_match");
  };

  const renderSection = () => {
    if (!analysis) return null;
    const cat = analysis.categories;
    switch(activeCategory) {
      case "ats_match": return <ATSSection data={cat.ats_match}/>;
      case "quantification": return <QuantifySection data={cat.quantification}/>;
      case "repetition": return <RepetitionSection data={cat.repetition}/>;
      case "contact": return <ContactSection data={cat.contact}/>;
      case "file_format": return <FileSection data={cat.file_format}/>;
      case "sections": return <SectionsSection data={cat.sections}/>;
      case "grammar": return <GrammarSection data={cat.grammar}/>;
      default: return null;
    }
  };

  return (
    <>
      <style>{css}</style>

      {/* NAV */}
      <nav className="nav">
        <button className="nav-logo" onClick={()=>{setPage("home");reset();}}>
          <span className="nav-logo-dot"/> ATSync
        </button>
        <div className="nav-links">
          <button className={`nav-link ${page==="coverletter"?"active":""}`} onClick={()=>setPage("coverletter")}>Cover Letter</button>
          <button className={`nav-link ${page==="howitworks"?"active":""}`} onClick={()=>setPage("howitworks")}>How it works</button>
          <button className="nav-btn" onClick={()=>{setPage("home");reset();}}>Check Resume</button>
        </div>
      </nav>

      {/* COVER LETTER PAGE */}
      {page === "coverletter" && <CoverLetterPage onBack={()=>setPage("home")}/>}

      {/* HOW IT WORKS PAGE */}
      {page === "howitworks" && <HowItWorksPage onBack={()=>setPage("home")}/>}

      {/* HOME */}
      {page === "home" && (
        <>
          {/* UPLOAD */}
          {subPage === "upload" && (
            <div className="hero-page">
              <div className="hero-left fu">
                <div className="ai-badge">✦ AI Powered · Free Resume Checker</div>
                <h1 className="hero-title">Is your resume<br/><span>good enough?</span></h1>
                <p className="hero-sub">A free AI resume checker doing 7 crucial checks to ensure your resume is ready to get you interview callbacks.</p>
                <div className="upload-card">
                  <label className="field-label">Resume (PDF)</label>
                  <div className="drop-zone">
                    <input type="file" accept=".pdf" onChange={e=>setFile(e.target.files[0])}/>
                    <span className="drop-icon">📄</span>
                    <p className="drop-text">{file?"":"Drop your resume here or choose a file"}</p>
                    <p className="drop-hint">{file?"":"PDF only · Max 2MB"}</p>
                    {file&&<p className="file-ok">✓ {file.name}</p>}
                  </div>
                  <label className="field-label">Job Description</label>
                  <textarea rows={4} value={jd} onChange={e=>setJd(e.target.value)}
                    placeholder="Paste job description for ATS match analysis..."/>
                  {error&&<div className="error-msg">{error}</div>}
                  <button className="btn btn-primary" onClick={handleAnalyze} disabled={loading}>
                    {loading?<><div className="spinner"/>Analyzing...</>:"Check My Resume →"}
                  </button>
                  <p className="privacy">🔒 Privacy guaranteed · Your data is never stored</p>
                </div>
              </div>
              <div className="hero-right fu2"><ResumeVisual/></div>
            </div>
          )}

          {/* LOADING */}
          {subPage === "loading" && (
            <div className="loading-page">
              <div className="loading-left">
                <p style={{fontSize:13,color:"var(--muted)",fontWeight:500,marginBottom:16}}>Your Score</p>
                <div style={{display:"flex",justifyContent:"center",marginBottom:24}}>
                  <div style={{width:90,height:90,borderRadius:"50%",background:"#f0f0ee"}}/>
                </div>
                {["CONTENT","SECTIONS","ATS ESSENTIALS","TAILORING"].map(label=>(
                  <div key={label} style={{marginBottom:16}}>
                    <p style={{fontSize:10,color:"var(--hint)",fontWeight:600,marginBottom:6}}>{label}</p>
                    <div className="skeleton" style={{width:"80%"}}/><div className="skeleton" style={{width:"60%"}}/>
                  </div>
                ))}
              </div>
              <div className="loading-right">
                <div className="checklist">
                  <h2 style={{fontSize:22,fontWeight:600,marginBottom:32,letterSpacing:"-0.02em"}}>Analyzing your resume...</h2>
                  {LOAD_STEPS.map((label,i)=>{
                    const status=i<loadStep?"done":i===loadStep?"active":"pending";
                    return (
                      <div key={i} className="check-item">
                        <div className={`check-icon ${status}`}>
                          {status==="done"?"✓":status==="active"?<div style={{width:16,height:16,border:"2px solid var(--info)",borderTopColor:"transparent",borderRadius:"50%",animation:"spin 0.8s linear infinite"}}/>:""}
                        </div>
                        <span className={`check-label ${status}`}>{label}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* RESULTS */}
          {subPage === "results" && analysis && (
            <div className="results-page">
              <div className="results-left">
                <div className="score-box">
                  <p className="score-box-label">Your Score</p>
                  <p className="score-box-num" style={{color:scoreColor(analysis.overall_score)}}>{analysis.overall_score}</p>
                  <div style={{display:"flex",justifyContent:"center",margin:"10px 0 4px"}}>
                    <ScoreCircle score={analysis.overall_score} size={110}/>
                  </div>
                  <p className="score-box-sub">{analysis.total_issues} issues found</p>
                </div>
                <p style={{fontSize:10,fontWeight:600,color:"var(--hint)",textTransform:"uppercase",letterSpacing:"0.08em",margin:"16px 0 8px 4px"}}>Checks</p>
                {CATEGORIES.map(({key,label,icon})=>{
                  const cat=analysis.categories[key];
                  return (
                    <div key={key} className={`cat-item ${activeCategory===key?"active":""}`}
                      onClick={()=>setActiveCategory(key)}>
                      <span className="cat-left">{icon} {label}</span>
                      {activeCategory!==key&&<CategoryBadge score={cat?.score??0}/>}
                    </div>
                  );
                })}
                <button className="back-btn" onClick={reset} style={{marginTop:20,paddingLeft:12}}>← Analyze another</button>
              </div>
              <div className="results-right">
                <button className="back-btn" onClick={reset}>← Back</button>
                {renderSection()}
              </div>
            </div>
          )}
        </>
      )}
    </>
  );
}