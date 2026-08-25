"""JD corpus rebuild diagnostic: re-run skills/JD-match and relevance
against the rebuilt, real-postings JD corpus (evaluation/jds_v2.json),
holding the seed taxonomy fixed against the original field-only
evaluation/jds.json (isolates the JD corpus as the only changed variable).

n=33 (the 33 resumes with a collected real posting), not n=38 -- the 5
resumes with no collected posting (R02, R04, R07, R09, R18) are excluded
outright, not backfilled with the old field-only JD. Backfilling would
mix a taxonomy-friendly-by-construction JD into the same n as genuinely
independent postings and contaminate exactly the comparison this rebuild
exists to make. See jds_v2.json's _provenance_note and
evaluation/backlog.md's opening section for the full reasoning.

Headline result, checked directly rather than inferred from a sample-size
drop: of the 33 real postings, the 92-term seed taxonomy matches ZERO
skills in 20 of them. That coverage failure is reported first, before any
correlation number -- a taxonomy that can't read the majority of real
postings in its own target fields can't be fairly judged on correlation
until the coverage failure itself is addressed.
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
ESCO_PATH = BACKEND_DIR / "data" / "skills_en.csv"
LABELS_PATH = EVAL_DIR / "labels.csv"
OLD_JDS_PATH = EVAL_DIR / "jds.json"
NEW_JDS_PATH = EVAL_DIR / "jds_v2.json"
RESUMES_DIR = EVAL_DIR / "step0" / "Resumes"


def _stats(pairs: list[tuple[float, float]], label: str) -> None:
    if len(pairs) < 3:
        print(f"  {label}: n={len(pairs)} (too few to fit)")
        return
    hs = [p[0] for p in pairs]
    ms = [p[1] for p in pairs]
    sl = linregress(hs, ms)
    rho, pval = spearmanr(hs, ms)
    print(
        f"  {label}: n={len(pairs)} slope={sl.slope:.3f} intercept={sl.intercept:.2f} "
        f"r2={sl.rvalue**2:.3f} rho={rho:.3f} (p={pval:.3f})"
    )


def _collected_new_jds() -> dict:
    new_jds = json.loads(NEW_JDS_PATH.read_text(encoding="utf-8"))
    return {
        rid: v for rid, v in new_jds.items()
        if rid != "_provenance_note" and v.get("text")
    }


def jd_coverage_diagnostic(matcher: SkillMatcher, jds: dict, label: str) -> set[str]:
    """Which resume ids' JD text matches zero taxonomy skills. Printed and
    returned so both this and the resume-side check share one code path.
    """
    zero = set()
    for rid, entry in jds.items():
        jd_norm = normalize_document_text(entry["text"])
        if not matcher.extract(jd_norm).skill_ids:
            zero.add(rid)
    print(f"=== {label}: JD-side coverage ===")
    print(f"  {len(jds) - len(zero)}/{len(jds)} JDs match at least one taxonomy skill")
    if zero:
        print(f"  zero-match: {sorted(zero)}")
    return zero


def resume_coverage_diagnostic(matcher: SkillMatcher, label: str) -> set[str]:
    """Same check on the resume side -- ρ=0.653 for no-JD skills mode was
    measured entirely on resumes matched against these same 92 terms; if
    resume-side coverage is thin too, that number needs a second look.
    """
    with LABELS_PATH.open(encoding="utf-8") as f:
        labels = list(csv.DictReader(f))
    zero = set()
    attempted = 0
    for row in labels:
        pdf_path = RESUMES_DIR / f"{row['id']}.pdf"
        if not pdf_path.exists():
            continue
        extracted = extract_document(pdf_path)
        if not extracted.is_readable:
            continue
        attempted += 1
        resume_text = normalize_document_text(extracted.text)
        if not matcher.extract(resume_text).skill_ids:
            zero.add(row["id"])
    print(f"=== {label}: resume-side coverage ===")
    print(f"  {attempted - len(zero)}/{attempted} resumes match at least one taxonomy skill")
    if zero:
        print(f"  zero-match: {sorted(zero)}")
    return zero


def main() -> None:
    with LABELS_PATH.open(encoding="utf-8") as f:
        labels = {row["id"]: row for row in csv.DictReader(f)}
    old_jds = json.loads(OLD_JDS_PATH.read_text(encoding="utf-8"))
    new_jds = _collected_new_jds()
    print(f"Collected JD corpus: n={len(new_jds)} (of 38 resumes; 5 uncollected, excluded)")
    print()

    seed_matcher = SkillMatcher(Taxonomy.from_seed_json(SEED_PATH))

    # --- Headline: coverage, not correlation, first ---
    seed_zero_jds = jd_coverage_diagnostic(seed_matcher, new_jds, "seed taxonomy, NEW real JDs")
    print()
    resume_coverage_diagnostic(seed_matcher, "seed taxonomy")
    print()

    if ESCO_PATH.exists():
        esco_matcher = SkillMatcher(Taxonomy.from_esco_csv(ESCO_PATH, filter_generic_aliases=True))
        esco_zero_jds = jd_coverage_diagnostic(esco_matcher, new_jds, "filtered ESCO, NEW real JDs")
        seed_covered = len(new_jds) - len(seed_zero_jds)
        esco_covered = len(new_jds) - len(esco_zero_jds)
        print(f"  -> coverage: seed {seed_covered}/{len(new_jds)}, ESCO {esco_covered}/{len(new_jds)} "
              f"(recovered {esco_covered - seed_covered} of the {len(seed_zero_jds)} seed zero-match JDs)")
        print()
    else:
        esco_matcher = None
        print(f"ESCO file not found at {ESCO_PATH} -- skipping ESCO coverage/correlation. See data/README.md.")
        print()

    # --- Correlation, on whatever base rate of coverage each taxonomy has ---
    def run(matcher: SkillMatcher, label: str) -> None:
        old_skills, new_skills = [], []
        old_rel, new_rel = [], []
        for rid, row in labels.items():
            pdf_path = RESUMES_DIR / f"{rid}.pdf"
            if not pdf_path.exists():
                continue
            extracted = extract_document(pdf_path)
            if not extracted.is_readable:
                continue
            resume_text = normalize_document_text(extracted.text)
            human_skills = float(row["skills"])
            human_relevance = float(row["relevance"])

            old_jd_text = old_jds.get(row["field"])
            if old_jd_text:
                jd_norm = normalize_document_text(old_jd_text)
                d = SkillsScorer().score(resume_text, jd_norm, matcher)
                if d.status == "scored":
                    old_skills.append((human_skills, d.score))
                d2 = RelevanceScorer().score(resume_text, jd_norm, matcher)
                if d2.status == "scored":
                    old_rel.append((human_relevance, d2.score))

            if rid in new_jds:
                jd_norm = normalize_document_text(new_jds[rid]["text"])
                d = SkillsScorer().score(resume_text, jd_norm, matcher)
                if d.status == "scored":
                    new_skills.append((human_skills, d.score))
                d2 = RelevanceScorer().score(resume_text, jd_norm, matcher)
                if d2.status == "scored":
                    new_rel.append((human_relevance, d2.score))

        print(f"=== {label}: skills/JD-match, OLD (contaminated) vs. NEW (n=33 real) JDs ===")
        _stats(old_skills, "OLD field-only JDs (n=38 available)")
        _stats(new_skills, "NEW real JDs (n=33 available) -- SELECTION BIAS: only")
        print("    taxonomy-covered JDs produce a score here; this subsample is the")
        print("    easy cases, not a random sample of the 33 -- an optimistic estimate")
        print("    of match-mode performance, not a neutral one.")
        print()
        print(f"=== {label}: relevance, OLD vs. NEW JDs ===")
        _stats(old_rel, "OLD field-only JDs")
        _stats(new_rel, "NEW real JDs (n=33 available)")
        print()

    run(seed_matcher, "SEED taxonomy")
    if esco_matcher is not None:
        run(esco_matcher, "ESCO (filtered) taxonomy")


if __name__ == "__main__":
    main()
