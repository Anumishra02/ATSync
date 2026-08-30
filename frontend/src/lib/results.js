import { STATUS_FALLBACK } from "@/lib/constants";

// A scored dimension at or above this fraction of its max reads as
// healthy (--ok); below it, weak (--warn). No failing/red state -- the
// palette doesn't have one, and a low score is a weak result, not an error.
export const OK_THRESHOLD = 0.6;

export function dimPct(dim) {
  if (dim.status !== "scored" || !dim.max_points) return 0;
  return dim.score / dim.max_points;
}

export function dimTone(dim) {
  if (dim.status !== "scored") return "absent";
  return dimPct(dim) >= OK_THRESHOLD ? "ok" : "warn";
}

export function dimReason(dim) {
  return dim.detail?.reason || STATUS_FALLBACK[dim.status] || "";
}

/**
 * Match mode scores out of 100 by construction; quality mode runs fewer
 * dimensions, so its score is renormalised from raw_score / available_points.
 * Surface that explicitly rather than letting a 66 look like 66/100.
 */
export function scoreCaption(analysis) {
  const { raw_score, available_points, mode } = analysis;
  const renorm = Math.round(available_points) !== 100;
  const base = `${round1(raw_score)} of ${round1(available_points)} points scored`;
  return renorm ? `${base} · renormalised` : base;
}

export function modeLabel(analysis) {
  return analysis.mode === "match" ? "RESUME + ROLE MATCH" : "RESUME QUALITY";
}

function round1(n) {
  return Number.isInteger(n) ? String(n) : n.toFixed(1);
}

// ---- Contact & Links -------------------------------------------------------
//
// The backend's phone/link extraction is greedy on purpose (it would
// rather over-collect candidates than miss a real one). Presentation's
// job is to show the findings a person can act on and quietly set aside
// the pattern noise -- date ranges caught by the phone regex, the same
// URL linked eight times -- without inventing or hiding a verified result.

export function buildContactFindings(contact, parse) {
  const findings = [];

  // Phones: prefer the valid one(s). If none are valid, show the single
  // best candidate as a problem. Extra invalid candidates are almost
  // always dates ("2023 - 05") -- note them once, don't list them.
  const phones = contact.phones || [];
  const validPhones = phones.filter((p) => p.is_valid);
  const invalidPhones = phones.filter((p) => !p.is_valid);
  if (validPhones.length) {
    for (const p of validPhones) {
      findings.push({
        kind: "phone",
        status: p.issue ? "warn" : "ok",
        label: "Phone",
        text: p.issue ? `${p.e164 || p.raw} — ${p.issue}` : `${p.e164 || p.raw} · valid, dialable`,
      });
    }
  } else if (invalidPhones.length) {
    const p = invalidPhones[0];
    findings.push({
      kind: "phone",
      status: "bad",
      label: "Phone",
      text: `${cleanRaw(p.raw)} — ${p.issue || "not a valid number"}`,
    });
  }
  const strayPhones = validPhones.length ? invalidPhones.length : Math.max(0, invalidPhones.length - 1);
  if (strayPhones > 0) {
    findings.push({
      kind: "phone-noise",
      status: "note",
      label: "Phone",
      text: `${strayPhones} other number-like string${strayPhones === 1 ? "" : "s"} in the text (dates, IDs) — ignored`,
    });
  }

  // Emails
  for (const e of contact.emails || []) {
    if (!e.is_valid_syntax) {
      findings.push({ kind: "email", status: "bad", label: "Email", text: `${e.raw} — ${e.issue || "invalid syntax"}` });
    } else if (e.is_deliverable === false) {
      findings.push({ kind: "email", status: "bad", label: "Email", text: `${e.raw} — domain doesn't accept mail` });
    } else if (e.is_deliverable === true) {
      findings.push({ kind: "email", status: "ok", label: "Email", text: `${e.raw} · deliverable (MX records found)` });
    } else {
      findings.push({ kind: "email", status: "ok", label: "Email", text: `${e.raw} · valid address` });
    }
  }

  // Links: dedupe, then one row each.
  const seen = new Set();
  for (const l of contact.links || []) {
    if (seen.has(l.url)) continue;
    seen.add(l.url);
    if (l.status === "unreachable") {
      findings.push({ kind: "link", status: "bad", label: "Link", text: `${prettyUrl(l.url)} unreachable` });
    } else if (l.status === "blocked") {
      findings.push({ kind: "link", status: "note", label: "Link", text: `${prettyUrl(l.url)} — host blocks automated checks` });
    } else if (l.platform_issue) {
      findings.push({ kind: "link", status: "warn", label: "Link", text: `${prettyUrl(l.url)} — ${l.platform_issue}` });
    } else {
      findings.push({ kind: "link", status: "ok", label: "Link", text: `${prettyUrl(l.url)} reachable` });
    }
  }

  // Unclickable URLs: present in the text, not a real link target. Skip
  // bare emails -- they're covered by the email rows, and "your email
  // isn't a hyperlink" isn't a finding worth a row.
  for (const u of parse?.unclickable_urls || []) {
    if (u.includes("@") && !u.includes("/")) continue;
    findings.push({
      kind: "unclickable",
      status: "warn",
      label: "Link",
      text: `${prettyUrl(u)} present as text, not clickable`,
    });
  }

  // Completeness gaps
  for (const m of contact.missing || []) {
    findings.push({ kind: "missing", status: "warn", label: "Missing", text: `No ${m} found in the header` });
  }

  return findings;
}

// Issues a reader should count -- the ✓ rows and pure notes don't.
export function countIssues(findings) {
  return findings.filter((f) => f.status === "bad" || f.status === "warn").length;
}

function cleanRaw(s) {
  return String(s).replace(/\s+/g, " ").trim();
}

function prettyUrl(u) {
  return String(u).replace(/^https?:\/\//, "").replace(/^www\./, "").replace(/\/$/, "");
}
