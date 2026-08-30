// Temporary home for the original App.js <style> block, lifted verbatim
// during the file split (step 2). Step 3 of the redesign replaces this
// wholesale with design tokens + Tailwind in index.css and a real shared
// shell -- nothing here is meant to survive that.
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

  .nav { position:fixed; top:0; left:0; right:0; z-index:100; background:rgba(248,248,246,0.9); backdrop-filter:blur(12px); border-bottom:0.5px solid var(--border); padding:0 48px; height:60px; display:flex; align-items:center; justify-content:space-between; }
  .nav-logo { font-size:20px; font-weight:700; letter-spacing:-0.03em; color:var(--text); display:flex; align-items:center; gap:8px; cursor:pointer; background:none; border:none; font-family:'Inter',sans-serif; }
  .nav-logo-dot { width:8px; height:8px; background:var(--accent); border-radius:50%; display:inline-block; }
  .nav-links { display:flex; align-items:center; gap:28px; }
  .nav-link { font-size:13px; color:var(--muted); cursor:pointer; transition:color 0.15s; background:none; border:none; font-family:'Inter',sans-serif; padding:0; }
  .nav-link:hover,.nav-link.active { color:var(--text); font-weight:500; }
  .nav-btn { font-size:13px; font-weight:500; color:#fff; background:var(--accent); padding:8px 18px; border-radius:8px; border:none; cursor:pointer; font-family:'Inter',sans-serif; transition:background 0.15s; }
  .nav-btn:hover { background:#4f46e5; }

  .hero-page { min-height:100vh; padding-top:60px; display:grid; grid-template-columns:1fr 1fr; }
  .hero-left { padding:80px 56px 80px 64px; display:flex; flex-direction:column; justify-content:center; border-right:0.5px solid var(--border); }
  .hero-right { display:flex; align-items:center; justify-content:center; padding:60px 48px; background:linear-gradient(135deg,#f0f0ff 0%,#f8f0ff 50%,#f0f8ff 100%); position:relative; overflow:hidden; }
  .ai-badge { display:inline-flex; align-items:center; gap:6px; background:var(--accent-light); color:var(--accent); font-size:11px; font-weight:600; padding:5px 14px; border-radius:999px; margin-bottom:24px; border:0.5px solid rgba(99,102,241,0.2); }
  .hero-title { font-size:clamp(32px,4vw,52px); font-weight:700; letter-spacing:-0.03em; line-height:1.12; margin-bottom:16px; }
  .hero-title span { color:var(--accent); }
  .hero-sub { font-size:15px; color:var(--muted); line-height:1.7; margin-bottom:36px; max-width:420px; }

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
  .privacy { font-size:12px; color:var(--hint); text-align:center; margin-top:12px; }
  .error-msg { font-size:13px; color:var(--danger); margin-top:10px; padding:10px 14px; background:var(--danger-bg); border-radius:8px; }
  .spinner { width:15px; height:15px; border:1.5px solid rgba(255,255,255,0.4); border-top-color:#fff; border-radius:50%; animation:spin 0.6s linear infinite; }

  .scene { position:relative; width:360px; height:420px; }
  .scene-bg-blob { position:absolute; border-radius:50%; filter:blur(40px); opacity:0.4; z-index:0; }

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

  /* COVER LETTER -- KEY FIX: always 2 columns, never collapses */
  .cl-page { min-height:100vh; padding-top:60px; display:grid; grid-template-columns:1fr 1fr; }
  .cl-left { padding:48px 40px 48px 56px; border-right:0.5px solid var(--border); overflow-y:auto; min-height:calc(100vh - 60px); }
  .cl-right { padding:48px 40px; background:linear-gradient(135deg,#f0f0ff,#f8f0ff); display:flex; flex-direction:column; min-height:calc(100vh - 60px); overflow-y:auto; }
  .cl-title { font-size:clamp(24px,3vw,38px); font-weight:700; letter-spacing:-0.03em; margin-bottom:10px; }
  .cl-sub { font-size:13px; color:var(--muted); margin-bottom:28px; line-height:1.65; }
  .tone-row { display:flex; gap:8px; margin-bottom:20px; flex-wrap:wrap; }
  .tone-btn { padding:6px 14px; border-radius:999px; border:0.5px solid var(--border); font-size:12px; font-weight:500; cursor:pointer; font-family:'Inter',sans-serif; background:var(--surface); color:var(--muted); transition:all 0.15s; }
  .tone-btn.active { background:var(--accent); color:#fff !important; border-color:var(--accent); }
  .tone-btn.active:hover { background:#4f46e5; color:#fff !important; }
  .tone-btn:not(.active):hover { border-color:var(--accent); color:var(--accent); }
  .cl-output { background:var(--surface); border-radius:16px; border:0.5px solid var(--border); padding:28px; flex:1; min-height:400px; position:relative; box-shadow:0 4px 24px rgba(0,0,0,0.06); overflow-y:auto; }
  .cl-output-placeholder { display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:360px; text-align:center; gap:12px; }
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
  .cl-loading { display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:360px; gap:16px; }
  .cl-spinner { width:32px; height:32px; border:2.5px solid var(--accent-light); border-top-color:var(--accent); border-radius:50%; animation:spin 0.8s linear infinite; }
  .cl-loading-text { font-size:14px; color:var(--muted); }

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
    .hero-page { grid-template-columns:1fr; }
    .hero-right { display:none; }
    .hero-left { padding:60px 24px; }
    .results-page,.loading-page { grid-template-columns:1fr; }
    .results-left { position:static; height:auto; }
    .results-right { padding:24px 20px; }
    .nav { padding:0 20px; }
    .nav-links { gap:16px; }
    .hiw-page { padding:80px 24px 60px; }
  }
`;

export default function GlobalStyles() {
  return <style>{css}</style>;
}
