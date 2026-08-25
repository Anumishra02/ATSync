"""Phase 1 item 2: 92-term seed taxonomy vs. ESCO (~13.9k terms), measured
side by side on the same 39-resume corpus, not asserted.

The taxonomy swap itself is a one-line change (SkillMatcher(Taxonomy.from_esco_csv(...))
instead of .from_seed_json(...)) -- see taxonomy.py, which already had both
loaders behind the same interface before this script was written. The
actual work here is producing the comparison, per the explicit brief: "keep
the loader pluggable... that comparison is the presentable artifact, not
the swap itself."

Requires backend/data/skills_en.csv (ESCO v1.1.1 classification, English) --
not committed to the repo (9.5MB external dataset; see data/README.md for
the fetch command). Prints a fetch reminder and exits if it's missing,
rather than silently reporting a partial (seed-only) comparison.

Headline result (see evaluation/backlog.md's ESCO section for the full
writeup): a naive swap is a measured regression (skills/no-JD ρ
0.653->0.212, tech-field subset saturates flat). Filtering ESCO's alias
list down to specific-enough surface forms (Taxonomy.from_esco_csv's
filter_generic_aliases, default True) recovers it substantially and, for
JD-match mode specifically, produces a real, significant improvement over
the seed taxonomy (ρ 0.294->0.477, p 0.070->0.002). The no-JD count mode
does not clearly improve overall and stays flat on the tech-field subset
regardless of _SKILLS_NO_JD_TARGET_COUNT -- checked across a range of
values, not assumed fixed by one.

JD-source independence (explicitly asked to confirm before running this):
evaluation/jds.json -- the 34 field-matched job descriptions used for
match-mode scoring below -- was committed in an earlier session, before
any ESCO file existed anywhere in this repository or its working tree.
Verified via `git log --diff-filter=A -- evaluation/jds.json`: that
commit predates this script and backend/data/skills_en.csv by construction,
so the JD text cannot have been drawn from or influenced by ESCO's own
skill descriptions -- there was nothing to draw from yet. This matters
because if JD text and taxonomy vocabulary shared a source, skill-match
scores would inflate for free, for a reason that has nothing to do with
whether the taxonomy is actually better.
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
JDS_PATH = EVAL_DIR / "jds.json"
RESUMES_DIR = EVAL_DIR / "step0" / "Resumes"

_TECH_FIELD_MARKERS = ("computer science", "software", "data science", "swe", "full-stack", "hci", "electrical eng")


def _is_tech_field(field: str) -> bool:
    low = field.lower()
    return any(m in low for m in _TECH_FIELD_MARKERS)


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


def main() -> None:
    if not ESCO_PATH.exists():
        print(f"ESCO file not found at {ESCO_PATH} -- see data/README.md. Aborting.")
        return

    with LABELS_PATH.open(encoding="utf-8") as f:
        labels = list(csv.DictReader(f))
    jds = json.loads(JDS_PATH.read_text(encoding="utf-8"))

    print("Loading taxonomies...")
    seed_tax = Taxonomy.from_seed_json(SEED_PATH)
    esco_raw_tax = Taxonomy.from_esco_csv(ESCO_PATH, filter_generic_aliases=False)
    esco_tax = Taxonomy.from_esco_csv(ESCO_PATH, filter_generic_aliases=True)
    print(f"  seed:            {seed_tax}")
    print(f"  esco (raw):      {esco_raw_tax}")
    print(f"  esco (filtered): {esco_tax}")
    print()

    taxonomies = {
        "seed": SkillMatcher(seed_tax),
        "esco_raw": SkillMatcher(esco_raw_tax),
        "esco_filtered": SkillMatcher(esco_tax),
    }

    # skills_no_jd[taxonomy] = [(human_skills, machine_score), ...], split overall/tech/non-tech
    results: dict[str, dict[str, list[tuple[float, float]]]] = {
        name: {"skills_no_jd": [], "skills_no_jd_tech": [], "skills_no_jd_nontech": [],
               "skills_jd": [], "relevance": []}
        for name in taxonomies
    }
    skill_counts: dict[str, list[int]] = {name: [] for name in taxonomies}
    taxonomy_covered = {name: 0 for name in taxonomies} | {"total": 0}

    for row in labels:
        pdf_path = RESUMES_DIR / f"{row['id']}.pdf"
        if not pdf_path.exists():
            continue
        extracted = extract_document(pdf_path)
        if not extracted.is_readable:
            continue
        resume_text = normalize_document_text(extracted.text)
        human_skills = float(row["skills"])
        human_relevance = float(row["relevance"])
        field = row["field"]
        jd_text = jds.get(field)
        tech_bucket = "skills_no_jd_tech" if _is_tech_field(field) else "skills_no_jd_nontech"

        for name, matcher in taxonomies.items():
            d_no_jd = SkillsScorer().score(resume_text, None, matcher)
            if d_no_jd.status == "scored":
                results[name]["skills_no_jd"].append((human_skills, d_no_jd.score))
                results[name][tech_bucket].append((human_skills, d_no_jd.score))
                skill_counts[name].append(d_no_jd.detail["skills_found"])

            if jd_text is not None:
                jd_norm = normalize_document_text(jd_text)
                d_jd = SkillsScorer().score(resume_text, jd_norm, matcher)
                if d_jd.status == "scored":
                    results[name]["skills_jd"].append((human_skills, d_jd.score))
                d_rel = RelevanceScorer().score(resume_text, jd_norm, matcher)
                if d_rel.status == "scored":
                    results[name]["relevance"].append((human_relevance, d_rel.score))

        if jd_text is not None:
            taxonomy_covered["total"] += 1
            jd_norm = normalize_document_text(jd_text)
            for name, matcher in taxonomies.items():
                if matcher.extract(jd_norm).skill_ids:
                    taxonomy_covered[name] += 1

    names = list(taxonomies)

    print("=== Skills, no-JD count mode, vs human 'skills' label ===")
    for name in names:
        _stats(results[name]["skills_no_jd"], f"{name:14s} overall")
    print()
    print("--- split by field ---")
    for name in names:
        _stats(results[name]["skills_no_jd_tech"], f"{name:14s} tech fields")
        _stats(results[name]["skills_no_jd_nontech"], f"{name:14s} non-tech fields")
    print()

    print("=== Skills, JD-match mode, vs human 'skills' label ===")
    for name in names:
        _stats(results[name]["skills_jd"], f"{name:14s}")
    print()

    print("=== Relevance (score_resume), vs human 'relevance' label ===")
    for name in names:
        _stats(results[name]["relevance"], f"{name:14s}")
    print()

    print("=== Raw skill-count coverage (no-JD mode) ===")
    import statistics
    for name in names:
        c = skill_counts[name]
        print(f"  {name:14s}: n={len(c)} mean={statistics.mean(c):.1f} median={statistics.median(c)} max={max(c)}")
    print()

    print("=== JD taxonomy coverage (does the matcher find ANY skill in the JD at all) ===")
    for name in names:
        cov = taxonomy_covered[name]
        tot = taxonomy_covered["total"]
        print(f"  {name:14s}: {cov}/{tot} JDs ({cov/tot:.0%})")


if __name__ == "__main__":
    main()
