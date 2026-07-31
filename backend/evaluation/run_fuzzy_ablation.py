"""Fuzzy-tier (tier 2) word-frequency threshold sweep, broken out by edit distance.

The original sweep was saturated -- recall sat at 1.000 from ratio-threshold
80 to 96, so the curve was flat and the 88.0 default was unjustified by it.
This one uses graded synthetic typos plus hard negatives drawn from ordinary
resume English that happens to sit near a skill name.

The fuzzy tier no longer uses a flat rapidfuzz ratio threshold -- it uses a
length-scaled edit-distance allowance (fixed, not swept: 1 edit up to 6
chars, 2 up to 12, 3 beyond -- see matcher.py) plus a `wordfreq` gate that
rejects candidates that are themselves common English words. This script
sweeps *that* gate's zipf-frequency cutoff, which is the knob that actually
trades recall against false positives now.

Usage:
    python evaluation/run_fuzzy_ablation.py
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.skills.matcher import SkillMatcher  # noqa: E402
from services.skills.taxonomy import Taxonomy  # noqa: E402

GOLD = ROOT / "evaluation" / "gold_fuzzy.json"
SEED = ROOT / "data" / "skills_seed.json"
WORD_FREQ_THRESHOLDS = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0]


def evaluate(matcher: SkillMatcher, gold: dict) -> dict:
    by_dist: dict[int, list[int]] = defaultdict(list)
    for case in gold["positives"]:
        got = matcher.extract(case["text"]).skill_ids
        by_dist[case["edit_distance"]].append(int(set(case["skills"]) <= got))

    tripped = 0
    trap_hits = 0
    for case in gold["hard_negatives"]:
        got = matcher.extract(case["text"]).skill_ids
        if got:
            tripped += 1
        trap_hits += len(got & set(case["traps"]))

    n_neg = len(gold["hard_negatives"]) or 1
    recalls = {d: sum(v) / len(v) for d, v in sorted(by_dist.items())}
    overall = sum(sum(v) for v in by_dist.values()) / sum(len(v) for v in by_dist.values())
    return {
        "by_dist": recalls,
        "overall": overall,
        "neg_rate": tripped / n_neg,
        "trap_hits": trap_hits,
    }


def main() -> int:
    gold = json.loads(GOLD.read_text(encoding="utf-8"))
    taxonomy = Taxonomy.from_seed_json(SEED)

    print(f"\npositives {len(gold['positives'])} (graded typos)   "
          f"hard negatives {len(gold['hard_negatives'])}\n")
    print(f"{'word_freq':>10}{'d=1':>8}{'d=2':>8}{'d=3':>8}"
          f"{'overall':>10}{'neg trip':>10}{'traps':>7}")
    print("-" * 61)

    rows = []
    for th in WORD_FREQ_THRESHOLDS:
        m = SkillMatcher(taxonomy, fuzzy_word_freq_threshold=th)
        r = evaluate(m, gold)
        rows.append((th, r))
        d = r["by_dist"]
        print(f"{th:>10.1f}{d.get(1, 0):>8.3f}{d.get(2, 0):>8.3f}{d.get(3, 0):>8.3f}"
              f"{r['overall']:>10.3f}{r['neg_rate']:>10.3f}{r['trap_hits']:>7}")

    recall_spread = max(r["overall"] for _, r in rows) - min(r["overall"] for _, r in rows)
    neg_spread = max(r["neg_rate"] for _, r in rows) - min(r["neg_rate"] for _, r in rows)
    print(f"\nrecall spread across the sweep: {recall_spread:.3f}   "
          f"neg-trip-rate spread: {neg_spread:.3f}")
    # Recall is expected to be flat here -- the word-freq gate trades off
    # against the trap rate, not recall (that's the edit-distance
    # allowance's job, which this script doesn't sweep). Only a set where
    # *neither* axis moves is actually uninformative.
    if recall_spread < 0.05 and neg_spread < 0.05:
        print("  WARNING: still saturated. Neither recall nor the trap rate moves")
        print("  across this sweep -- add heavier typos or closer negatives before")
        print("  claiming any threshold is justified.")
        return 0

    # Operating point: hard negatives are the expensive error here, so require
    # zero trap hits and then take the best recall available.
    clean = [(th, r) for th, r in rows if r["trap_hits"] == 0]
    if clean:
        th, r = max(clean, key=lambda x: x[1]["overall"])
        print(f"\nHighest recall with zero trap hits: threshold {th:.1f} "
              f"(d=1 {r['by_dist'].get(1, 0):.3f}, overall {r['overall']:.3f})")
    else:
        print("\nEvery threshold hits at least one trap -- the ambiguity gate, "
              "not the threshold, is what has to carry these.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
