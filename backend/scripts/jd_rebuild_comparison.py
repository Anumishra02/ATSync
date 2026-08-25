"""Re-run the skills/JD-match and relevance comparison against the rebuilt
JD corpus (evaluation/jds_v2.json -- one real, field+level-matched posting
per resume, 33/38 genuinely new, see its _provenance_note and
evaluation/backlog.md's JD rebuild section) and compare against the
original field-only jds.json, using ONLY the seed taxonomy (holding the
taxonomy fixed isolates whether the JD rebuild itself moves the number,
per the explicit diagnostic: "If seed-JD skills jumps from 0.294 toward
0.65, the JDs were the problem. If it doesn't, the conditioning logic is.").
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from scipy.stats import linregress, spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.analysis.scorers import RelevanceScorer, SkillsScorer
from services.matching.chunking import normalize_document_text
from services.parsing.pdf_extract import extract_document
from services.skills.matcher import SkillMatcher
from services.skills.taxonomy import Taxonomy

BACKEND_DIR = Path(__file__).resolve().parents[1]
EVAL_DIR = BACKEND_DIR.parent / "evaluation"
SEED_PATH = BACKEND_DIR / "data" / "skills_seed.json"
LABELS_PATH = EVAL_DIR / "labels.csv"
OLD_JDS_PATH = EVAL_DIR / "jds.json"
NEW_JDS_PATH = EVAL_DIR / "jds_v2.json"
RESUMES_DIR = EVAL_DIR / "step0" / "Resumes"


def _stats(pairs: list[tuple[float, float]], label: str) -> None:
    hs = [p[0] for p in pairs]
    ms = [p[1] for p in pairs]
    sl = linregress(hs, ms)
    rho, pval = spearmanr(hs, ms)
    print(
        f"  {label}: n={len(pairs)} slope={sl.slope:.3f} intercept={sl.intercept:.2f} "
        f"r2={sl.rvalue**2:.3f} rho={rho:.3f} (p={pval:.3f})"
    )


def main() -> None:
    with LABELS_PATH.open(encoding="utf-8") as f:
        labels = list(csv.DictReader(f))
    old_jds = json.loads(OLD_JDS_PATH.read_text(encoding="utf-8"))
    new_jds = json.loads(NEW_JDS_PATH.read_text(encoding="utf-8"))

    matcher = SkillMatcher(Taxonomy.from_seed_json(SEED_PATH))

    old_skills, new_skills = [], []
    old_rel, new_rel = [], []
    new_skills_real_only, new_rel_real_only = [], []
    fallback_ids = {k for k, v in new_jds.items() if isinstance(v, dict) and v.get("is_fallback")}

    for row in labels:
        rid = row["id"]
        pdf_path = RESUMES_DIR / f"{rid}.pdf"
        if not pdf_path.exists() or rid not in new_jds:
            continue
        extracted = extract_document(pdf_path)
        if not extracted.is_readable:
            continue
        resume_text = normalize_document_text(extracted.text)
        human_skills = float(row["skills"])
        human_relevance = float(row["relevance"])

        old_jd_text = old_jds.get(row["field"])
        new_jd_text = new_jds[rid]["text"]

        if old_jd_text:
            jd_norm = normalize_document_text(old_jd_text)
            d = SkillsScorer().score(resume_text, jd_norm, matcher)
            if d.status == "scored":
                old_skills.append((human_skills, d.score))
            d2 = RelevanceScorer().score(resume_text, jd_norm, matcher)
            if d2.status == "scored":
                old_rel.append((human_relevance, d2.score))

        if new_jd_text:
            jd_norm = normalize_document_text(new_jd_text)
            d = SkillsScorer().score(resume_text, jd_norm, matcher)
            if d.status == "scored":
                new_skills.append((human_skills, d.score))
                if rid not in fallback_ids:
                    new_skills_real_only.append((human_skills, d.score))
            d2 = RelevanceScorer().score(resume_text, jd_norm, matcher)
            if d2.status == "scored":
                new_rel.append((human_relevance, d2.score))
                if rid not in fallback_ids:
                    new_rel_real_only.append((human_relevance, d2.score))

    print("=== Skills, JD-match mode, seed taxonomy fixed ===")
    _stats(old_skills, "OLD JDs (field-only, one per field)")
    _stats(new_skills, "NEW JDs (all 38, incl. 5 fallback)")
    _stats(new_skills_real_only, "NEW JDs (33 real, field+level-matched only)")
    print()

    print("=== Relevance (score_resume), seed taxonomy fixed ===")
    _stats(old_rel, "OLD JDs (field-only, one per field)")
    _stats(new_rel, "NEW JDs (all 38, incl. 5 fallback)")
    _stats(new_rel_real_only, "NEW JDs (33 real, field+level-matched only)")


if __name__ == "__main__":
    main()
