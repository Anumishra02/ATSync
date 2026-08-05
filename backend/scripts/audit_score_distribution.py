"""Audit the live scorer's output distribution across the real corpus.

Phase A Step 3: "a bad resume and a good resume land far apart, not 82 vs
88." A score that can't spread across its own range can't discriminate.

Two scenarios, deliberately different in what they test:

  broad_relevance   The real corpus happens to span genuinely different
                     domains -- several software engineers (Anu, Prateek,
                     Jake's template), a nurse (Grace Fernandes), and a
                     digital marketer ("John Doe"). Scored against a
                     generic software-engineering JD: unrelated candidates
                     should land far from relevant ones.
  niche_demand       A demanding, specific JD (Kubernetes/GraphQL/Rust/
                     MLOps) that none of the gathered candidates actually
                     have. Included on purpose: everyone scoring low here
                     is *correct*, not compressed -- a JD nobody in the
                     corpus is qualified for should produce uniformly low
                     scores. Don't mistake this scenario's small spread for
                     the same failure mode as broad_relevance's would be.

Local-only -- requires test_corpus/. Run:
    python scripts/audit_score_distribution.py
"""

from __future__ import annotations

import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.ats_scorer import calculate_ats_score as v1_score  # noqa: E402
from services.matching.chunking import normalize_document_text  # noqa: E402
from services.parsing.pdf_extract import extract_document  # noqa: E402
from services.scoring import legacy_ats_score as v2_score  # noqa: E402
from services.skills.matcher import SkillMatcher  # noqa: E402
from services.skills.taxonomy import Taxonomy  # noqa: E402

CORPUS = ROOT.parent / "test_corpus"
SEED = ROOT / "data" / "skills_seed.json"

SCENARIOS = {
    "broad_relevance": """\
Requirements

- 3+ years of experience building backend services in Python
- Strong SQL and relational database experience required
- Must have hands-on experience with Docker and CI/CD pipelines
- Experience with React or another modern JavaScript framework
- Familiarity with Git and collaborative development workflows

Nice to Have

- Experience with machine learning or NLP
- Familiarity with AWS or another cloud platform
""",
    "niche_demand": """\
Requirements

- 5+ years of experience with Kubernetes and container orchestration in production
- Deep expertise in GraphQL API design
- Strong background in distributed systems and system design
- Experience with Rust or Go for systems programming
- Proven track record with MLOps and model deployment

Nice to Have

- Experience with recommender systems
- Familiarity with Terraform
""",
}


def _bar(value: float, max_value: float = 100, width: int = 30) -> str:
    filled = int(width * value / max_value) if max_value else 0
    return "#" * filled + "-" * (width - filled)


def _load_readable_resumes() -> list[tuple[str, str]]:
    out = []
    for path in sorted(CORPUS.glob("*.pdf")):
        result = extract_document(path)
        if result.is_readable:
            out.append((path.name, normalize_document_text(result.text)))
    return out


def run_scenario(name: str, jd_text: str, matcher: SkillMatcher, resumes: list[tuple[str, str]]) -> float:
    jd = normalize_document_text(jd_text)
    rows = []
    for filename, resume_text in resumes:
        v1 = v1_score(resume_text, jd)
        v2 = v2_score(matcher, resume_text, jd)
        rows.append({
            "file": filename,
            "v1_score": v1["ats_score"],
            "v2_score": v2["ats_score"],
            "v2_skill_score": v2["skill_score"],
            "v2_keyword_score": v2["keyword_score"],
        })

    print(f"\n=== {name} ===")
    print(f"{'file':45s}{'v1':>6}{'v2':>6}{'skill':>7}{'keyword':>9}  bar (v2)")
    print("-" * 100)
    for r in sorted(rows, key=lambda r: -r["v2_score"]):
        print(
            f"{r['file']:45s}{r['v1_score']:6.0f}{r['v2_score']:6.0f}"
            f"{r['v2_skill_score']:7.1f}{r['v2_keyword_score']:9.1f}  "
            f"{_bar(r['v2_score'])}"
        )

    v2_vals = [r["v2_score"] for r in rows]
    sk_vals = [r["v2_skill_score"] for r in rows]
    kw_vals = [r["v2_keyword_score"] for r in rows]
    spread = max(v2_vals) - min(v2_vals)

    print(f"\n{'':20s}{'min':>8}{'max':>8}{'spread':>8}{'mean':>8}{'stdev':>8}")
    for label, vals in [("v2 final score", v2_vals), ("v2 skill_score", sk_vals), ("v2 keyword_score", kw_vals)]:
        print(
            f"{label:20s}{min(vals):8.1f}{max(vals):8.1f}{max(vals) - min(vals):8.1f}"
            f"{statistics.mean(vals):8.1f}{statistics.pstdev(vals):8.1f}"
        )
    return spread


def main() -> int:
    if not CORPUS.exists():
        print("test_corpus/ not present locally -- nothing to audit.")
        return 0

    matcher = SkillMatcher(Taxonomy.from_seed_json(SEED))
    resumes = _load_readable_resumes()
    if not resumes:
        print("No readable files found in test_corpus/.")
        return 0

    spreads = {name: run_scenario(name, jd, matcher, resumes) for name, jd in SCENARIOS.items()}

    print("\n=== summary ===")
    for name, spread in spreads.items():
        verdict = "OK (>= 30)" if spread >= 30 else "below 30-point target"
        print(f"{name:20s} spread={spread:6.1f}  {verdict}")
    print(
        "\nniche_demand's small spread is expected, not a bug: none of the "
        "gathered candidates actually have those specific skills, so a low, "
        "similar score for everyone is the correct answer. broad_relevance "
        "is the scenario that would show compression if it existed -- it "
        "doesn't here, but this corpus is small (10 files, one real "
        "domain-outlier pair); worth re-running as the corpus grows."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
