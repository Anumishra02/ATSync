"""Head-to-head: v1 substring scorer vs v2 cascade matcher.

This is the seed of the evaluation harness. Twenty hand-labeled snippets is
not a benchmark — it is a smoke test that proves the direction is right and
gives us the table shape we will later fill with 150 real pairs.

Run:  python scripts/compare_v1_v2.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.eval_common import GOLD, evaluate  # noqa: E402
from services.skills.matcher import SkillMatcher  # noqa: E402
from services.skills.taxonomy import Taxonomy  # noqa: E402

# v1 used lowercase display strings, not ids. Map them onto v2 ids so the
# comparison is apples to apples.
V1_TO_V2 = {
    "python": "python", "javascript": "javascript", "c++": "cpp", "java": "java",
    "typescript": "typescript", "sql": "sql", "node.js": "nodejs",
    "express.js": "express", "fastapi": "fastapi", "django": "django",
    "flask": "flask", "rest api": "rest-api", "restful api": "rest-api",
    "restful apis": "rest-api", "jwt": "jwt", "authentication": None,
    "rbac": "rbac", "react": "react", "next.js": "nextjs", "tailwind": "tailwind",
    "html": "html", "css": "css", "machine learning": "machine-learning",
    "deep learning": "deep-learning", "nlp": "nlp", "xgboost": "xgboost",
    "scikit-learn": "scikit-learn", "pandas": "pandas", "numpy": "numpy",
    "tensorflow": "tensorflow", "pytorch": "pytorch",
    "collaborative filtering": "recommender-systems", "mongodb": "mongodb",
    "postgresql": "postgresql", "mysql": "mysql", "redis": "redis",
    "docker": "docker", "kubernetes": "kubernetes", "git": "git",
    "github": "git", "ci/cd": "cicd", "aws": "aws",
    "data structures": "data-structures", "algorithms": "algorithms",
    "object-oriented programming": "oop", "oop": "oop",
    "system design": "system-design", "problem solving": "problem-solving",
    "socket.io": "websockets", "websockets": "websockets",
}


if __name__ == "__main__":
    taxonomy = Taxonomy.from_seed_json(ROOT / "data" / "skills_seed.json")
    matcher = SkillMatcher(taxonomy)

    from services.ats_scorer import extract_skills as v1_extract  # noqa: E402

    def v1(text: str) -> set[str]:
        out = set()
        for raw in v1_extract(text):
            mapped = V1_TO_V2.get(raw)
            if mapped:
                out.add(mapped)
        return out

    def v2(text: str) -> set[str]:
        return matcher.extract(text).skill_ids

    # v1's entire vocabulary, expressed as v2 ids — the fair comparison set.
    v1_vocab = {v for v in V1_TO_V2.values() if v}

    rows = [
        evaluate(v1, "v1  substring match", restrict_to=v1_vocab),
        evaluate(v2, "v2  cascade (exact+fuzzy)", restrict_to=v1_vocab),
    ]

    print(f"\nScored on {len(GOLD)} hand-labeled snippets, "
          f"restricted to v1's {len(v1_vocab)}-skill vocabulary\n")
    print(f"{'system':<28}{'TP':>4}{'FP':>4}{'FN':>4}"
          f"{'precision':>11}{'recall':>9}{'F1':>8}")
    print("-" * 68)
    for row in rows:
        print(f"{row['name']:<28}{row['tp']:>4}{row['fp']:>4}{row['fn']:>4}"
              f"{row['precision']:>11.3f}{row['recall']:>9.3f}{row['f1']:>8.3f}")

    print("\nFalse positives produced by v1:")
    for text, wrong in rows[0]["examples"]:
        print(f"  - {wrong:<18} in  \"{text}\"")
    if not rows[1]["examples"]:
        print("\nFalse positives produced by v2: none")
    else:
        print("\nFalse positives produced by v2:")
        for text, wrong in rows[1]["examples"]:
            print(f"  - {wrong:<18} in  \"{text}\"")

    print("\nv2 on its full taxonomy (no vocabulary restriction):")
    full = evaluate(v2, "v2 full", restrict_to=None)
    print(f"  precision {full['precision']:.3f}  "
          f"recall {full['recall']:.3f}  F1 {full['f1']:.3f}")
