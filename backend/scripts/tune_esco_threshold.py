"""A4: tune esco-skill-extractor's cosine-similarity threshold on JDs
OUTSIDE the 33-JD eval corpus (evaluation/threshold_tuning_holdout.json --
8 live Greenhouse postings from Asana and Gusto, neither of which appears
in jds_v2.json's 33; see that file's own provenance note).

Builds the SkillExtractor's embeddings ONCE (the slow, one-time cost) and
sweeps the threshold by calling its internal `_get_entity` directly with
different threshold values against the same precomputed embeddings --
verified against esco_skill_extractor's own source that this is
equivalent to constructing a fresh SkillExtractor per threshold (same
similarity_matrix, same argmax, only the final `> threshold` filter
differs), just without paying the embedding-build cost N times.

Prints coverage/count per threshold plus resolved skill labels (from
data/skills_en.csv's conceptUri -> preferredLabel) for manual inspection --
there's no human quality label on this held-out set, so "which threshold
is best" is a judgment call made by reading the actual matches, not a
number optimized against. That's stated as a limitation, not hidden.

Run (from backend/):
    python scripts/tune_esco_threshold.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.matching.chunking import normalize_document_text  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]
EVAL_DIR = BACKEND_DIR.parent / "evaluation"
HOLDOUT_PATH = EVAL_DIR / "threshold_tuning_holdout.json"
ESCO_CSV = BACKEND_DIR / "data" / "skills_en.csv"

THRESHOLDS = [0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75]


def load_label_lookup() -> dict[str, str]:
    lookup = {}
    with ESCO_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            lookup[row["conceptUri"]] = row["preferredLabel"]
    return lookup


def main() -> int:
    holdout = json.loads(HOLDOUT_PATH.read_text(encoding="utf-8"))
    docs = {k: normalize_document_text(v["text"]) for k, v in holdout.items() if not k.startswith("_")}
    doc_labels = ", ".join(f"{k} ({holdout[k]['title']})" for k in docs)
    print(f"Held-out JDs: {len(docs)} ({doc_labels})")

    print("\nBuilding ESCO embeddings once (slow, one-time)...")
    from esco_skill_extractor import SkillExtractor

    se = SkillExtractor()  # default threshold irrelevant, we call _get_entity directly

    label_lookup = load_label_lookup()
    ids, texts = list(docs.keys()), list(docs.values())

    print(f"\n{'threshold':>10s}{'coverage':>10s}{'mean/doc':>10s}{'median':>8s}{'max':>6s}")
    per_threshold_results: dict[float, list[list[str]]] = {}
    for t in THRESHOLDS:
        results = se._get_entity(texts, se._skill_ids, se._skill_embeddings, t)
        per_threshold_results[t] = results
        counts = [len(r) for r in results]
        covered = sum(1 for c in counts if c > 0)
        mean_c = sum(counts) / len(counts)
        median_c = sorted(counts)[len(counts) // 2]
        print(f"{t:10.2f}{covered:6d}/{len(docs):<3d}{mean_c:10.1f}{median_c:8d}{max(counts):6d}")

    print("\n=== Sample matches at each threshold, for manual precision inspection ===")
    sample_id = "asana_marketing"  # a non-technical JD -- exactly where the main benchmark's signal was weakest
    idx = ids.index(sample_id)
    print(f"Sample doc: {sample_id} ({holdout[sample_id]['title']})\n")
    for t in THRESHOLDS:
        uris = per_threshold_results[t][idx]
        names = sorted(label_lookup.get(u, u) for u in uris)
        print(f"  threshold={t:.2f} ({len(names)} skills): {names}")

    print(f"\n=== Same inspection for a technical JD (asana_ds -- Data Scientist) ===\n")
    idx2 = ids.index("asana_ds")
    for t in THRESHOLDS:
        uris = per_threshold_results[t][idx2]
        names = sorted(label_lookup.get(u, u) for u in uris)
        print(f"  threshold={t:.2f} ({len(names)} skills): {names}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
