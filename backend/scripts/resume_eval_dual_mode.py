"""Evaluate the Phase 0 dual-mode analysis pipeline against the 39-resume
human-labeled corpus.

Distinct from resume_eval_predict.py/report.py, which evaluate the OLD
live pipeline (legacy_ats_score -> full_analysis). This evaluates the NEW
one (services.analysis.run_analysis) in both modes, on the same corpus,
so the two systems' numbers are never accidentally conflated in one file.

For each labeled resume:
  - quality_score  = run_analysis(resume, jd=None).score       (mode="quality")
  - match_score    = run_analysis(resume, jd=field_jd).score   (mode="match")
  - human_quality  = (human_total - human_relevance) / 85 * 100
                      -- the "total minus relevance" trick: no new labels
                      needed, since removing relevance's 15 points from
                      the human's 100-point total and rescaling to /85 is
                      exactly what a human "quality-only" rating would
                      have been, under the same rubric quality mode uses.
                      Comparing this to quality_score is the actual test
                      of whether no-JD mode carries real signal, not an
                      assumption that it does.

Coverage (a resume's mode is "complete" when every dimension that mode
runs came back status="scored", none "uncomputable") is reported
separately from the correlation numbers, same principle as
resume_eval_report.py's taxonomy_covered split: a coverage gap and a
scoring-quality problem are different failure modes and conflating them
into one number hides which one to fix.

Run (from backend/):
    python scripts/resume_eval_dual_mode.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.analysis.models import AnalysisResult  # noqa: E402
from services.analysis.pipeline import run_analysis  # noqa: E402
from services.matching.chunking import normalize_document_text  # noqa: E402
from services.parsing.pdf_extract import extract_document  # noqa: E402
from services.skills.matcher import SkillMatcher  # noqa: E402
from services.skills.taxonomy import Taxonomy  # noqa: E402

EVAL_DIR = ROOT.parent / "evaluation"
LABELS_PATH = EVAL_DIR / "labels.csv"
JDS_PATH = EVAL_DIR / "jds.json"
RESUMES_DIR = EVAL_DIR / "step0" / "Resumes"
OUT_PATH = EVAL_DIR / "predictions_dual_mode.csv"
SEED = ROOT / "data" / "skills_seed.json"

QUALITY_MAX_POINTS = 85  # 100 - relevance's 15, per Resume-Scores-39.xlsx's rubric

OUT_HEADER = [
    "id", "field", "quality_score", "quality_complete",
    "match_score", "match_complete",
    "human_total", "human_relevance", "human_quality_pct",
    "uncomputable_dims_quality", "uncomputable_dims_match",
]


def _is_complete(result: AnalysisResult) -> bool:
    """Every dimension the mode runs came back scored -- no uncomputable
    ones. (not_applicable dimensions, i.e. relevance in quality mode,
    don't count against completeness -- they're correctly not running,
    not failing to run.)
    """
    return not any(d.status == "uncomputable" for d in result.dimensions)


def _uncomputable_names(result: AnalysisResult) -> str:
    return ",".join(d.dimension for d in result.dimensions if d.status == "uncomputable")


def evaluate_one(matcher: SkillMatcher, resume_id: str, field: str, jd_text: str | None, row: dict) -> dict:
    pdf_path = RESUMES_DIR / f"{resume_id}.pdf"
    extraction = extract_document(pdf_path)
    resume_text = normalize_document_text(extraction.text)

    quality = run_analysis(resume_text, None, matcher)
    match = run_analysis(resume_text, normalize_document_text(jd_text), matcher) if jd_text else None

    human_total = float(row["total"])
    human_relevance = float(row["relevance"])
    human_quality_pct = round((human_total - human_relevance) / QUALITY_MAX_POINTS * 100, 1)

    return {
        "id": resume_id,
        "field": field,
        "quality_score": quality.score,
        "quality_complete": _is_complete(quality),
        "match_score": match.score if match else "",
        "match_complete": _is_complete(match) if match else "",
        "human_total": human_total,
        "human_relevance": human_relevance,
        "human_quality_pct": human_quality_pct,
        "uncomputable_dims_quality": _uncomputable_names(quality),
        "uncomputable_dims_match": _uncomputable_names(match) if match else "",
    }


def main() -> int:
    if not LABELS_PATH.exists():
        print(f"Missing {LABELS_PATH} -- run resume_eval_freeze_labels.py first.")
        return 1

    jds = json.loads(JDS_PATH.read_text(encoding="utf-8"))
    matcher = SkillMatcher(Taxonomy.from_seed_json(SEED))

    with LABELS_PATH.open(encoding="utf-8") as f:
        labels = list(csv.DictReader(f))

    rows = []
    for row in labels:
        resume_id, field = row["id"], row["field"]
        pdf_path = RESUMES_DIR / f"{resume_id}.pdf"
        if not pdf_path.exists():
            print(f"  SKIP {resume_id}: no PDF at {pdf_path}")
            continue
        jd_text = jds.get(field)
        try:
            rows.append(evaluate_one(matcher, resume_id, field, jd_text, row))
        except Exception as e:
            print(f"  ERROR {resume_id}: {e!r}")
            continue

    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_HEADER)
        writer.writeheader()
        writer.writerows(rows)

    print("=" * 60)
    print("ATSync Dual-Mode Evaluation")
    print("=" * 60)
    print(f"\n{'id':6s}{'field':28s}{'quality':>10}{'match':>8}{'human_q':>9}")
    print("-" * 65)
    for r in rows:
        match_disp = f"{r['match_score']:.0f}/100" if r["match_score"] != "" else "  --  "
        print(
            f"{r['id']:6s}{r['field'][:26]:28s}{r['quality_score']:>6.0f}/100"
            f"{match_disp:>8}{r['human_quality_pct']:>9.1f}"
        )

    n = len(rows)
    quality_complete = sum(1 for r in rows if r["quality_complete"])
    match_complete = sum(1 for r in rows if r["match_complete"] is True)
    match_attempted = sum(1 for r in rows if r["match_score"] != "")

    print(f"\nCoverage:")
    print(f"  Quality Mode: {quality_complete}/{n}")
    print(f"  Match Mode:   {match_complete}/{match_attempted} ({match_attempted}/{n} had a field-matched JD)")

    human_q = [r["human_quality_pct"] for r in rows]
    machine_q = [r["quality_score"] for r in rows]
    rho, p = spearmanr(human_q, machine_q)
    mae = sum(abs(h - m) for h, m in zip(human_q, machine_q)) / n

    print(f"\nQuality mode vs human (total - relevance, rescaled to /85 -> /100):")
    print(f"  n={n}  rho={rho:.3f}  p={p:.4f}  MAE={mae:.2f}")
    print(f"  (this is the actual test of whether no-JD mode carries signal --")
    print(f"   not assumed, measured)")

    print(f"\nWrote {n} rows to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
