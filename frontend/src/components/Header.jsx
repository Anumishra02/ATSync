// Nav lifted from the original App.js. `page` is the current route key,
// `onNavigate(key)` switches route, `onHome()` also resets the analyze
// flow. The shared shell in step 3 restyles this.
export default function Header({ page, onNavigate, onHome }) {
  return (
    <nav className="nav">
      <button className="nav-logo" onClick={onHome}>
        <span className="nav-logo-dot" /> ATSync
      </button>
      <div className="nav-links">
        <button
          className={`nav-link ${page === "coverletter" ? "active" : ""}`}
          onClick={() => onNavigate("coverletter")}
        >
          Cover Letter
        </button>
        <button
          className={`nav-link ${page === "howitworks" ? "active" : ""}`}
          onClick={() => onNavigate("howitworks")}
        >
          How it works
        </button>
        <button className="nav-btn" onClick={onHome}>
          Check Resume
        </button>
      </div>
    </nav>
  );
}
