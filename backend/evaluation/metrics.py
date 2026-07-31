"""Ranking metrics for Phase 2 retrieval.

Written before the retriever exists, deliberately. Declaring the measure
first is what stopped the semantic tier from shipping on vibes, and the same
discipline applies here: the bi-encoder has to beat a lexical baseline on
these numbers or it does not go in.

Relevance is graded, not binary:

    2  this resume bullet is direct evidence for the requirement
    1  partial / related evidence
    0  irrelevant

Graded labels matter because "close but not quite" is the interesting case
in resume matching, and binary labels throw that signal away.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def dcg(gains: Sequence[float], k: int | None = None) -> float:
    """Discounted cumulative gain with the standard 2^g - 1 formulation."""
    if k is not None:
        gains = gains[:k]
    return sum((2**g - 1) / math.log2(i + 2) for i, g in enumerate(gains))


def ndcg_at_k(ranked_relevance: Sequence[float], k: int = 5) -> float:
    """nDCG@k for one query.

    ``ranked_relevance[i]`` is the graded relevance of the item the system
    placed at rank i. Returns 0.0 when no relevant item exists, which is the
    right answer: an unanswerable query should not inflate the mean.
    """
    ideal = sorted(ranked_relevance, reverse=True)
    denom = dcg(ideal, k)
    if denom == 0:
        return 0.0
    return dcg(ranked_relevance, k) / denom


def mrr(ranked_relevance: Sequence[float], threshold: float = 1.0) -> float:
    """Reciprocal rank of the first item at or above ``threshold``."""
    for i, rel in enumerate(ranked_relevance):
        if rel >= threshold:
            return 1.0 / (i + 1)
    return 0.0


def recall_at_k(ranked_relevance: Sequence[float], total_relevant: int,
                k: int = 5, threshold: float = 1.0) -> float:
    """Fraction of all relevant items that appear in the top k."""
    if total_relevant <= 0:
        return 0.0
    hits = sum(1 for rel in ranked_relevance[:k] if rel >= threshold)
    return hits / total_relevant


def precision_at_k(ranked_relevance: Sequence[float], k: int = 5,
                   threshold: float = 1.0) -> float:
    if k <= 0:
        return 0.0
    return sum(1 for rel in ranked_relevance[:k] if rel >= threshold) / k


def aggregate(per_query: Sequence[Sequence[float]], totals: Sequence[int],
              k: int = 5) -> dict[str, float]:
    """Mean metrics across queries.

    ``totals[i]`` is the number of relevant items that exist for query i,
    which recall needs and the ranked list alone cannot tell you.
    """
    if not per_query:
        return {"ndcg@k": 0.0, "mrr": 0.0, "recall@k": 0.0, "precision@k": 0.0, "n": 0}
    n = len(per_query)
    return {
        f"ndcg@{k}": sum(ndcg_at_k(r, k) for r in per_query) / n,
        "mrr": sum(mrr(r) for r in per_query) / n,
        f"recall@{k}": sum(
            recall_at_k(r, t, k) for r, t in zip(per_query, totals, strict=True)
        ) / n,
        f"precision@{k}": sum(precision_at_k(r, k) for r in per_query) / n,
        "n": n,
    }
