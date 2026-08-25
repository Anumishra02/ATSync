"""Evaluation Step 2: run every labeled resume through the live pipeline.

For each row in evaluation/labels.csv, extracts the matching PDF from
evaluation/step0/Resumes/, scores it against the field-matched JD in
evaluation/jds.json (a marketing JD for the marketing resumes, a DS JD for
the Data Science / ML resume, etc. -- see that file), through the exact code
path the live /analyze route uses: extract_document -> normalize ->
legacy_ats_score -> full_analysis. Nothing is computed or judged here --
this step only dumps machine output next to the (not-yet-loaded) human
labels, into evaluation/predictions.csv.

Machine columns, and how they map onto the human rubric's six dimensions
(see evaluation/README.md for the full mapping rationale):

  machine_total        <- full_analysis's overall_score (0-100 blended score)
  machine_relevance     <- legacy_ats_score's keyword_score (JD keyword overlap)
  machine_skills         <- legacy_ats_score's skill_score (taxonomy skill coverage)
  machine_achievements  <- quantification score (% of bullets with numbers)
  machine_writing        <- repetition score (grammar score is also captured,
                            separately, but see the caveat below)
  machine_structure      <- mean(sections, contact, file_format) scores
  machine_experience     <- no column: ATSync has no dimension that scores
                            experience depth/ordering/completeness at all.
                            Recorded as blank on every row, on purpose --
                            see evaluation/README.md.

Also recorded: parse_status (from PDF extraction, so a low score can be
traced to a parse failure before it's blamed on the scorer) and raw grammar
score. Grammar requires GEMINI_API_KEY (backend/.env) to produce real
signal; without it, check_grammar's except branch returns a constant 85 for
every resume, which is why machine_writing uses repetition instead of
grammar as the primary proxy.

taxonomy_covered / jd_skill_count -- the most important column here. The
skill taxonomy (data/skills_seed.json) is 92 skills, almost entirely
software/data/devops -- accounting, art history, biology, policy, etc. have
essentially no vocabulary in it. Blending every field into one correlation
number would let that coverage gap masquerade as a scoring-quality problem,
so it's flagged per row instead of discovered later: jd_skill_count is how
many distinct taxonomy skills the matcher actually finds when it reads that
field's own JD (via legacy_ats_score's total_jd_skills -- the JD is the
right thing to test, not the resume, since a resume can only be scored on
skills the JD is capable of asking for). taxonomy_covered is that count
thresholded at >=6, which is an empirical split, not a hand-picked one: for
all 34 fields, jd_skill_count clusters as {20,15,13,12,11,8,7,7,7,6} for
software/data/CS-adjacent fields, then drops to {5,4,4,4,...,1} for
everything else (marketing gets partial credit for GA4/SEO, most others get
1-3 incidental matches on generic tools like Excel or "communication").
Step 3 must report Spearman/MAE split by this flag, not blended.

Run (from backend/):
    python scripts/resume_eval_predict.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.analyzer import full_analysis  # noqa: E402
from services.matching.chunking import normalize_document_text  # noqa: E402
from services.parsing.pdf_extract import extract_document  # noqa: E402
from services.scoring import legacy_ats_score  # noqa: E402
from services.skills.matcher import SkillMatcher  # noqa: E402
from services.skills.taxonomy import Taxonomy  # noqa: E402

EVAL_DIR = ROOT.parent / "evaluation"
LABELS_PATH = EVAL_DIR / "labels.csv"
JDS_PATH = EVAL_DIR / "jds.json"
RESUMES_DIR = EVAL_DIR / "step0" / "Resumes"
OUT_PATH = EVAL_DIR / "predictions.csv"
SEED = ROOT / "data" / "skills_seed.json"

# See module docstring: the natural break in matched-skill counts across the
# 34 field-matched JDs falls between 6 and 5, and it lines up exactly with
# which fields are software/data/CS-adjacent. Not tuned to fit a narrative --
# it's the only threshold that separates {20,15,13,12,11,8,7,7,7,6} from
# {5,4,...,1} without splitting either cluster.
TAXONOMY_COVERAGE_MIN_SKILLS = 6

OUT_HEADER = [
    "id", "field", "taxonomy_covered", "jd_skill_count",
    "machine_total", "machine_relevance", "machine_skills",
    "machine_achievements", "machine_writing", "machine_structure",
    "machine_experience",
    # raw components, kept for anyone who wants a different mapping later
    "ats_score", "skill_score", "keyword_score",
    "quantification_score", "repetition_score", "grammar_score",
    "sections_score", "contact_score", "file_format_score",
    "parse_status", "chars_extracted",
]


def score_one(matcher: SkillMatcher, resume_id: str, field: str, jd_text: str) -> dict:
    pdf_path = RESUMES_DIR / f"{resume_id}.pdf"
    result = extract_document(pdf_path)
    resume_text = normalize_document_text(result.text)
    jd_norm = normalize_document_text(jd_text)

    ats = legacy_ats_score(matcher, resume_text, jd_norm)
    analysis = full_analysis(resume_text, f"{resume_id}.pdf", pdf_path.stat().st_size, jd_norm, ats)
    cats = analysis["categories"]

    structure_score = round(
        (cats["sections"]["score"] + cats["contact"]["score"] + cats["file_format"]["score"]) / 3, 1
    )

    jd_skill_count = ats["total_jd_skills"]
    return {
        "id": resume_id,
        "field": field,
        "taxonomy_covered": jd_skill_count >= TAXONOMY_COVERAGE_MIN_SKILLS,
        "jd_skill_count": jd_skill_count,
        "machine_total": analysis["overall_score"],
        "machine_relevance": ats["keyword_score"],
        "machine_skills": ats["skill_score"],
        "machine_achievements": cats["quantification"]["score"],
        "machine_writing": cats["repetition"]["score"],
        "machine_structure": structure_score,
        "machine_experience": "",
        "ats_score": ats["ats_score"],
        "skill_score": ats["skill_score"],
        "keyword_score": ats["keyword_score"],
        "quantification_score": cats["quantification"]["score"],
        "repetition_score": cats["repetition"]["score"],
        "grammar_score": cats["grammar"]["score"],
        "sections_score": cats["sections"]["score"],
        "contact_score": cats["contact"]["score"],
        "file_format_score": cats["file_format"]["score"],
        "parse_status": result.parse_status,
        "chars_extracted": len(result.text),
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
        jd_text = jds.get(field)
        if jd_text is None:
            print(f"  SKIP {resume_id}: no JD for field {field!r}")
            continue
        pdf_path = RESUMES_DIR / f"{resume_id}.pdf"
        if not pdf_path.exists():
            print(f"  SKIP {resume_id}: no PDF at {pdf_path}")
            continue
        try:
            out = score_one(matcher, resume_id, field, jd_text)
        except Exception as e:
            print(f"  ERROR {resume_id}: {e!r}")
            continue
        rows.append(out)
        cov = "covered" if out["taxonomy_covered"] else "NOT covered"
        print(
            f"  {resume_id:5s} {field:38s} total={out['machine_total']:5.1f}  "
            f"parse={out['parse_status']}  taxonomy={cov} (jd_skills={out['jd_skill_count']})"
        )

    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_HEADER)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)}/{len(labels)} predictions to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
