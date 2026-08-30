// The original App.js <style> block, lifted during the file split and now
// scoped under `.legacy` so it can't fight the real design tokens in
// index.css. App.jsx wraps the not-yet-redesigned pages in
// <div className="legacy">; each page sheds this as it's rebuilt (steps
// 4–7), and the whole file goes when the last one does.
const css = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

  @keyframes legacyFadeUp { from { opacity:0; transform:translateY(14px); } to { opacity:1; transform:translateY(0); } }
  @keyframes legacySpin { to { transform: rotate(360deg); } }
  @keyframes legacyFloat { 0%,100%{transform:translateY(0px) rotate(-2deg);} 50%{transform:translateY(-12px) rotate(2deg);} }
  @keyframes legacyFloatB { 0%,100%{transform:translateY(0px) rotate(3deg);} 50%{transform:translateY(-8px) rotate(-1deg);} }
  @keyframes legacyFloatC { 0%,100%{transform:translateY(0px);} 50%{transform:translateY(-10px);} }
  @keyframes legacyShimmer { to { background-position: -200% 0; } }
  @keyframes legacyCheckIn { from{opacity:0;transform:scale(0.5);} to{opacity:1;transform:scale(1);} }

  .legacy {
    --bg: #f8f8f6; --surface: #ffffff; --border: rgba(0,0,0,0.08);
    --text: #1a1a1a; --muted: #6b7280; --hint: #9ca3af;
    --success: #16a34a; --success-bg: #f0fdf4;
    --danger: #dc2626; --danger-bg: #fef2f2;
    --warning: #d97706; --warning-bg: #fffbeb;
    --info: #2563eb; --info-bg: #eff6ff;
    --accent: #6366f1; --accent-light: #eef2ff;

    background: var(--bg); color: var(--text); font-family: 'Inter', system-ui, sans-serif;
    min-height: 100vh;
  }

  .legacy *, .legacy *::before, .legacy *::after { box-sizing: border-box; margin: 0; padding: 0; }

  /* These pages are now rendered inside the shared shell's <main>, which
     already clears the 60px fixed header. Drop the legacy self-offset and
     shrink the full-height panels by the header so they don't overflow.
     All of this dies with the page it targets (steps 4–7). */
  .legacy .hero-page, .legacy .cl-page, .legacy .loading-page, .legacy .results-page { padding-top: 0; min-height: calc(100vh - 60px); }
  .legacy .hiw-page { padding-top: 40px; }
  .legacy .results-left { top: 60px; }

  .legacy .fu{animation:legacyFadeUp 0.5s ease both;}
  .legacy .fu2{animation:legacyFadeUp 0.5s 0.1s ease both;}
  .legacy .fu3{animation:legacyFadeUp 0.5s 0.2s ease both;}

  .legacy .nav { position:fixed; top:0; left:0; right:0; z-index:100; background:rgba(248,248,246,0.9); backdrop-filter:blur(12px); border-bottom:0.5px solid var(--border); padding:0 48px; height:60px; display:flex; align-items:center; justify-content:space-between; }
  .legacy .nav-logo { font-size:20px; font-weight:700; letter-spacing:-0.03em; color:var(--text); display:flex; align-items:center; gap:8px; cursor:pointer; background:none; border:none; font-family:'Inter',sans-serif; }
  .legacy .nav-logo-dot { width:8px; height:8px; background:var(--accent); border-radius:50%; display:inline-block; }
  .legacy .nav-links { display:flex; align-items:center; gap:28px; }
  .legacy .nav-link { font-size:13px; color:var(--muted); cursor:pointer; transition:color 0.15s; background:none; border:none; font-family:'Inter',sans-serif; padding:0; }
  .legacy .nav-link:hover,.legacy .nav-link.active { color:var(--text); font-weight:500; }
  .legacy .nav-btn { font-size:13px; font-weight:500; color:#fff; background:var(--accent); padding:8px 18px; border-radius:8px; border:none; cursor:pointer; font-family:'Inter',sans-serif; transition:background 0.15s; }
  .legacy .nav-btn:hover { background:#4f46e5; }

  .legacy .hero-page { min-height:100vh; padding-top:60px; display:grid; grid-template-columns:1fr 1fr; }
  .legacy .hero-left { padding:80px 56px 80px 64px; display:flex; flex-direction:column; justify-content:center; border-right:0.5px solid var(--border); }
  .legacy .hero-right { display:flex; align-items:center; justify-content:center; padding:60px 48px; background:linear-gradient(135deg,#f0f0ff 0%,#f8f0ff 50%,#f0f8ff 100%); position:relative; overflow:hidden; }
  .legacy .ai-badge { display:inline-flex; align-items:center; gap:6px; background:var(--accent-light); color:var(--accent); font-size:11px; font-weight:600; padding:5px 14px; border-radius:999px; margin-bottom:24px; border:0.5px solid rgba(99,102,241,0.2); }
  .legacy .hero-title { font-size:clamp(32px,4vw,52px); font-weight:700; letter-spacing:-0.03em; line-height:1.12; margin-bottom:16px; }
  .legacy .hero-title span { color:var(--accent); }
  .legacy .hero-sub { font-size:15px; color:var(--muted); line-height:1.7; margin-bottom:36px; max-width:420px; }

  .legacy .upload-card { background:var(--surface); border-radius:16px; padding:28px; border:0.5px solid var(--border); box-shadow:0 4px 24px rgba(0,0,0,0.06); }
  .legacy .field-label { font-size:11px; font-weight:600; letter-spacing:0.06em; text-transform:uppercase; color:var(--muted); margin-bottom:8px; display:block; }
  .legacy .drop-zone { border:1.5px dashed rgba(0,0,0,0.14); border-radius:12px; padding:28px 20px; text-align:center; cursor:pointer; transition:all 0.2s; position:relative; margin-bottom:18px; background:var(--bg); }
  .legacy .drop-zone:hover { border-color:var(--accent); background:var(--accent-light); }
  .legacy .drop-zone input { position:absolute; inset:0; opacity:0; cursor:pointer; width:100%; height:100%; }
  .legacy .drop-icon { font-size:28px; margin-bottom:8px; display:block; }
  .legacy .drop-text { font-size:13px; color:var(--muted); margin-bottom:3px; }
  .legacy .drop-hint { font-size:11px; color:var(--hint); }
  .legacy .file-ok { font-size:13px; color:var(--success); margin-top:6px; font-weight:500; }
  .legacy textarea { width:100%; background:var(--bg); border:0.5px solid rgba(0,0,0,0.1); border-radius:10px; padding:12px 14px; color:var(--text); font-size:13px; font-family:'Inter',sans-serif; resize:none; outline:none; transition:border 0.2s; line-height:1.6; }
  .legacy textarea:focus { border-color:var(--accent); }
  .legacy textarea::placeholder { color:var(--hint); }
  .legacy .btn { display:inline-flex; align-items:center; justify-content:center; gap:8px; width:100%; padding:13px 20px; border-radius:10px; border:none; font-size:14px; font-weight:600; font-family:'Inter',sans-serif; cursor:pointer; transition:all 0.2s; margin-top:14px; }
  .legacy .btn-primary { background:var(--accent); color:#fff; }
  .legacy .btn-primary:hover { background:#4f46e5; transform:translateY(-1px); box-shadow:0 4px 12px rgba(99,102,241,0.3); }
  .legacy .btn-primary:disabled { opacity:0.5; cursor:not-allowed; transform:none; box-shadow:none; }
  .legacy .btn-ghost { background:var(--surface); color:var(--muted); border:0.5px solid var(--border); }
  .legacy .btn-ghost:hover { color:var(--text); }
  .legacy .privacy { font-size:12px; color:var(--hint); text-align:center; margin-top:12px; }
  .legacy .error-msg { font-size:13px; color:var(--danger); margin-top:10px; padding:10px 14px; background:var(--danger-bg); border-radius:8px; }
  .legacy .spinner { width:15px; height:15px; border:1.5px solid rgba(255,255,255,0.4); border-top-color:#fff; border-radius:50%; animation:legacySpin 0.6s linear infinite; }

  .legacy .loading-page { min-height:100vh; display:grid; grid-template-columns:320px 1fr; padding-top:60px; }
  .legacy .loading-left { background:var(--surface); border-right:0.5px solid var(--border); padding:40px 24px; }
  .legacy .loading-right { padding:80px 64px; display:flex; align-items:flex-start; }
  .legacy .skeleton { background:linear-gradient(90deg,#f0f0ee 25%,#e8e8e6 50%,#f0f0ee 75%); background-size:200% 100%; animation:legacyShimmer 1.5s infinite; border-radius:6px; height:10px; margin-bottom:8px; }
  .legacy .checklist { width:100%; max-width:440px; }
  .legacy .check-item { display:flex; align-items:center; gap:16px; padding:18px 0; border-bottom:0.5px solid var(--border); }
  .legacy .check-item:last-child { border-bottom:none; }
  .legacy .check-icon { width:30px; height:30px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:14px; flex-shrink:0; }
  .legacy .check-icon.done { background:var(--success-bg); color:var(--success); animation:legacyCheckIn 0.3s ease both; }
  .legacy .check-icon.active { background:var(--info-bg); }
  .legacy .check-icon.pending { background:#f5f5f4; }
  .legacy .check-label { font-size:16px; }
  .legacy .check-label.done { color:var(--text); font-weight:500; }
  .legacy .check-label.active { color:var(--text); font-weight:500; }
  .legacy .check-label.pending { color:var(--hint); }

  .legacy .results-page { min-height:100vh; display:grid; grid-template-columns:300px 1fr; padding-top:60px; }
  .legacy .results-left { background:var(--surface); border-right:0.5px solid var(--border); padding:28px 16px; position:sticky; top:60px; height:calc(100vh - 60px); overflow-y:auto; box-shadow:4px 0 20px rgba(0,0,0,0.04); }
  .legacy .results-right { padding:40px 48px; max-width:760px; }
  .legacy .score-box { background:linear-gradient(135deg,var(--accent-light),#f5f0ff); border-radius:14px; padding:24px 16px; text-align:center; margin-bottom:20px; border:0.5px solid rgba(99,102,241,0.15); }
  .legacy .score-box-label { font-size:13px; color:var(--muted); font-weight:500; margin-bottom:12px; }
  .legacy .score-box-num { font-size:64px; font-weight:700; letter-spacing:-0.04em; line-height:1; }
  .legacy .score-box-sub { font-size:12px; color:var(--muted); margin-top:8px; }
  .legacy .cat-item { display:flex; align-items:center; justify-content:space-between; padding:10px 12px; border-radius:10px; margin-bottom:3px; cursor:pointer; transition:all 0.15s; }
  .legacy .cat-item:hover { background:var(--bg); }
  .legacy .cat-item.active { background:var(--accent); color:white; }
  .legacy .cat-left { display:flex; align-items:center; gap:8px; font-size:13px; font-weight:500; }
  .legacy .cat-badge { font-size:11px; font-weight:600; padding:2px 8px; border-radius:999px; }
  .legacy .section-card { background:var(--surface); border-radius:16px; border:0.5px solid var(--border); padding:28px; margin-bottom:16px; animation:legacyFadeUp 0.3s ease both; box-shadow:0 2px 12px rgba(0,0,0,0.04); }
  .legacy .section-card h2 { font-size:16px; font-weight:600; margin-bottom:6px; }
  .legacy .section-desc { font-size:13px; color:var(--muted); margin-bottom:18px; line-height:1.65; }
  .legacy .score-bar-track { background:#f0f0ee; border-radius:999px; height:6px; margin:12px 0 16px; overflow:hidden; }
  .legacy .score-bar-fill { height:100%; border-radius:999px; transition:width 1.2s cubic-bezier(0.4,0,0.2,1); }
  .legacy .check-row { display:flex; align-items:center; justify-content:space-between; padding:10px 0; border-bottom:0.5px solid var(--border); font-size:13px; }
  .legacy .check-row:last-child { border-bottom:none; }
  .legacy .tip-box { background:#fffbeb; border:0.5px solid #fcd34d; border-radius:10px; padding:14px; margin-top:16px; font-size:13px; color:#92400e; line-height:1.6; }
  .legacy .back-btn { display:flex; align-items:center; gap:6px; font-size:13px; color:var(--muted); cursor:pointer; margin-bottom:24px; transition:color 0.15s; background:none; border:none; font-family:'Inter',sans-serif; padding:0; }
  .legacy .back-btn:hover { color:var(--text); }

  .legacy .cl-page { min-height:100vh; padding-top:60px; display:grid; grid-template-columns:1fr 1fr; }
  .legacy .cl-left { padding:48px 40px 48px 56px; border-right:0.5px solid var(--border); overflow-y:auto; min-height:calc(100vh - 60px); }
  .legacy .cl-right { padding:48px 40px; background:linear-gradient(135deg,#f0f0ff,#f8f0ff); display:flex; flex-direction:column; min-height:calc(100vh - 60px); overflow-y:auto; }
  .legacy .cl-title { font-size:clamp(24px,3vw,38px); font-weight:700; letter-spacing:-0.03em; margin-bottom:10px; }
  .legacy .cl-sub { font-size:13px; color:var(--muted); margin-bottom:28px; line-height:1.65; }
  .legacy .tone-row { display:flex; gap:8px; margin-bottom:20px; flex-wrap:wrap; }
  .legacy .tone-btn { padding:6px 14px; border-radius:999px; border:0.5px solid var(--border); font-size:12px; font-weight:500; cursor:pointer; font-family:'Inter',sans-serif; background:var(--surface); color:var(--muted); transition:all 0.15s; }
  .legacy .tone-btn.active { background:var(--accent); color:#fff !important; border-color:var(--accent); }
  .legacy .tone-btn.active:hover { background:#4f46e5; color:#fff !important; }
  .legacy .tone-btn:not(.active):hover { border-color:var(--accent); color:var(--accent); }
  .legacy .cl-output { background:var(--surface); border-radius:16px; border:0.5px solid var(--border); padding:28px; flex:1; min-height:400px; position:relative; box-shadow:0 4px 24px rgba(0,0,0,0.06); overflow-y:auto; }
  .legacy .cl-output-placeholder { display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:360px; text-align:center; gap:12px; }
  .legacy .cl-placeholder-icon { font-size:48px; opacity:0.3; }
  .legacy .cl-placeholder-text { font-size:14px; color:var(--hint); }
  .legacy .cl-letter { font-size:13px; line-height:1.9; color:var(--text); white-space:pre-wrap; }
  .legacy .cl-subject { background:var(--accent-light); border-radius:10px; padding:12px 16px; margin-bottom:20px; font-size:13px; font-weight:500; color:var(--accent); }
  .legacy .cl-subject span { color:var(--muted); font-weight:400; margin-right:6px; }
  .legacy .cl-points { margin-bottom:20px; }
  .legacy .cl-point { display:flex; gap:10px; font-size:13px; color:var(--muted); margin-bottom:8px; align-items:flex-start; }
  .legacy .cl-point-dot { width:6px; height:6px; background:var(--accent); border-radius:50%; margin-top:5px; flex-shrink:0; }
  .legacy .copy-btn { position:absolute; top:16px; right:16px; padding:6px 14px; border-radius:8px; border:0.5px solid var(--border); background:var(--bg); font-size:12px; font-weight:500; cursor:pointer; font-family:'Inter',sans-serif; color:var(--muted); transition:all 0.15s; }
  .legacy .copy-btn:hover { color:var(--text); border-color:var(--accent); }
  .legacy .cl-loading { display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:360px; gap:16px; }
  .legacy .cl-spinner { width:32px; height:32px; border:2.5px solid var(--accent-light); border-top-color:var(--accent); border-radius:50%; animation:legacySpin 0.8s linear infinite; }
  .legacy .cl-loading-text { font-size:14px; color:var(--muted); }

  .legacy .hiw-page { min-height:100vh; padding:100px 64px 80px; max-width:900px; margin:0 auto; }
  .legacy .hiw-title { font-size:clamp(32px,5vw,48px); font-weight:700; letter-spacing:-0.03em; margin-bottom:12px; text-align:center; }
  .legacy .hiw-title span { color:var(--accent); }
  .legacy .hiw-sub { font-size:15px; color:var(--muted); text-align:center; margin-bottom:72px; line-height:1.7; }
  .legacy .hiw-steps { display:flex; flex-direction:column; gap:0; }
  .legacy .hiw-step { display:grid; grid-template-columns:80px 1fr; gap:32px; position:relative; padding-bottom:48px; }
  .legacy .hiw-step:last-child { padding-bottom:0; }
  .legacy .hiw-step-left { display:flex; flex-direction:column; align-items:center; }
  .legacy .hiw-num { width:48px; height:48px; border-radius:50%; background:var(--accent); color:#fff; display:flex; align-items:center; justify-content:center; font-size:16px; font-weight:700; flex-shrink:0; z-index:1; }
  .legacy .hiw-line { width:2px; background:linear-gradient(180deg,var(--accent),var(--accent-light)); flex:1; margin-top:8px; border-radius:999px; }
  .legacy .hiw-step:last-child .hiw-line { display:none; }
  .legacy .hiw-content { padding-top:10px; }
  .legacy .hiw-step-title { font-size:18px; font-weight:600; margin-bottom:8px; }
  .legacy .hiw-step-desc { font-size:14px; color:var(--muted); line-height:1.7; margin-bottom:16px; }
  .legacy .hiw-step-card { background:var(--surface); border-radius:14px; border:0.5px solid var(--border); padding:18px 20px; box-shadow:0 2px 12px rgba(0,0,0,0.04); }
  .legacy .hiw-step-card-row { display:flex; align-items:center; gap:10px; font-size:13px; color:var(--muted); padding:6px 0; border-bottom:0.5px solid var(--border); }
  .legacy .hiw-step-card-row:last-child { border-bottom:none; }
  .legacy .hiw-icon { font-size:16px; }

  @media (max-width:900px) {
    .legacy .hero-page { grid-template-columns:1fr; }
    .legacy .hero-right { display:none; }
    .legacy .hero-left { padding:60px 24px; }
    .legacy .results-page,.legacy .loading-page { grid-template-columns:1fr; }
    .legacy .results-left { position:static; height:auto; }
    .legacy .results-right { padding:24px 20px; }
    .legacy .nav { padding:0 20px; }
    .legacy .nav-links { gap:16px; }
    .legacy .hiw-page { padding:80px 24px 60px; }
  }
`;

export default function GlobalStyles() {
  return <style>{css}</style>;
}
