"""Run retrievers against the Phase 2 gold set.

    python evaluation/run_retrieval_eval.py
    python evaluation/run_retrieval_eval.py --gold evaluation/gold_retrieval.json
    python evaluation/run_retrieval_eval.py --agreement a.json b.json

Every result is printed against `RandomRetriever`. An nDCG@5 of 0.55 reads
well until random scores 0.50 on the same set -- at which point the gold set
is too small or too easy, and the number says nothing about the system.
Publishing the floor next to the score makes that impossible to miss.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.matching.retrieval import BM25Retriever, RandomRetriever  # noqa: E402
from evaluation.gold import Pair, agreement_report, load_gold  # noqa: E402
from evaluation.metrics import aggregate  # noqa: E402

DEFAULT_GOLD = ROOT / "evaluation" / "gold_retrieval_example.json"


def evaluate_retriever(retriever, pairs: list[Pair], k: int = 5) -> dict:
    per_query: list[list[float]] = []
    totals: list[int] = []
    empty = 0

    for pair in pairs:
        retriever.index(pair.resume_chunks)
        for req in pair.requirements:
            hits = retriever.retrieve(req.text, k=k)
            if not hits:
                empty += 1
            ranked_texts = [h.chunk.text for h in hits]
            per_query.append(pair.relevance_for(req.text, ranked_texts))
            totals.append(pair.total_relevant(req.text))

    out = aggregate(per_query, totals, k=k)
    out["empty_result_rate"] = empty / len(per_query) if per_query else 0.0
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default=str(DEFAULT_GOLD))
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--agreement", nargs=2, metavar=("A", "B"),
                    help="two annotator gold files; report kappa and exit")
    args = ap.parse_args()

    if args.agreement:
        a, b = (load_gold(p, strict=False) for p in args.agreement)
        rep = agreement_report(a, b)
        print(f"\nshared judgements: {rep['n']}   "
              f"only in A: {rep['only_a']}   only in B: {rep['only_b']}")
        print(f"exact agreement:   {rep['exact']:.3f}")
        print(f"weighted kappa:    {rep['kappa']:.3f}")
        print(f"label distribution: {rep.get('label_distribution')}")
        if rep["kappa"] < 0.60:
            print("\n  kappa below 0.60 -- tighten the rubric using the")
            print("  disagreements below as worked examples, then re-label.")
            print("  Do NOT compute nDCG against labels this noisy.")
        print(f"\ntop disagreements ({len(rep['disagreements'])} total):")
        for d in rep["disagreements"][:10]:
            print(f"  [{d['a']} vs {d['b']}] {d['requirement'][:44]}")
            print(f"              -> {d['evidence'][:60]}")
        return 0

    pairs = load_gold(args.gold)
    n_queries = sum(len(p.requirements) for p in pairs)
    print(f"\npairs {len(pairs)}   requirements (queries) {n_queries}   k={args.k}")
    if len(pairs) < 5:
        print("  NOTE: this is a pilot-sized set. Treat the numbers as a")
        print("  smoke test of the harness, not as a result.")

    systems = [("Random (floor)", RandomRetriever(seed=7)), ("BM25", BM25Retriever())]

    print(f"\n{'system':<18}{'nDCG@'+str(args.k):>10}{'MRR':>8}"
          f"{'recall@'+str(args.k):>11}{'prec@'+str(args.k):>9}{'empty':>8}")
    print("-" * 64)
    results = {}
    for name, sys_ in systems:
        r = evaluate_retriever(sys_, pairs, k=args.k)
        results[name] = r
        print(f"{name:<18}{r[f'ndcg@{args.k}']:>10.3f}{r['mrr']:>8.3f}"
              f"{r[f'recall@{args.k}']:>11.3f}{r[f'precision@{args.k}']:>9.3f}"
              f"{r['empty_result_rate']:>8.3f}")

    lift = results["BM25"][f"ndcg@{args.k}"] - results["Random (floor)"][f"ndcg@{args.k}"]
    print(f"\nBM25 lift over random: {lift:+.3f}")
    if lift < 0.10:
        print("  BM25 is barely beating chance. Before blaming the retriever,")
        print("  check the gold set: too few bullets per resume, or labels")
        print("  concentrated on one grade, both flatten this number.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
