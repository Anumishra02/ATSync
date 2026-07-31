"""Tests for Phase 2 metrics and retrieval baselines.

Metrics get hand-computed expected values. A metric implementation that is
subtly wrong is worse than none -- every downstream conclusion inherits the
error, and nothing about the number looks suspicious.
"""

from __future__ import annotations

import math

import pytest

from services.matching.chunking import chunk_resume
from services.matching.retrieval import BM25Retriever, RandomRetriever, Retriever
from evaluation.metrics import aggregate, mrr, ndcg_at_k, precision_at_k, recall_at_k

RESUME = """\
EXPERIENCE

• Deployed and scaled services on Kubernetes across three regions
• Migrated the primary datastore to PostgreSQL and tuned slow queries
• Built a React frontend with Redux state management
• Wrote the CI/CD pipeline on GitHub Actions with automated tests
• Trained a classifier in PyTorch for document categorisation
"""


class TestMetrics:
    def test_perfect_ranking_scores_one(self):
        assert ndcg_at_k([2, 1, 0, 0, 0], k=5) == pytest.approx(1.0)

    def test_reversed_ranking_scores_less_than_perfect(self):
        assert ndcg_at_k([0, 0, 0, 1, 2], k=5) < ndcg_at_k([2, 1, 0, 0, 0], k=5)

    def test_no_relevant_items_scores_zero_not_nan(self):
        # An unanswerable query must not inflate the mean.
        assert ndcg_at_k([0, 0, 0], k=3) == 0.0

    def test_ndcg_matches_hand_computation(self):
        # gains [1, 2]: DCG = (2^1-1)/log2(2) + (2^2-1)/log2(3) = 1 + 3/1.58496
        # ideal [2, 1]: DCG = 3/1 + 1/1.58496
        got = ndcg_at_k([1, 2], k=2)
        want = (1 + 3 / math.log2(3)) / (3 + 1 / math.log2(3))
        assert got == pytest.approx(want)

    def test_graded_relevance_beats_binary_treatment(self):
        # A '2' at rank 0 must outrank a '1' at rank 0.
        assert ndcg_at_k([2, 0], k=2) == 1.0
        assert ndcg_at_k([1, 2], k=2) < 1.0

    @pytest.mark.parametrize(
        ("ranked", "expected"),
        [([1, 0, 0], 1.0), ([0, 1, 0], 0.5), ([0, 0, 1], 1 / 3), ([0, 0, 0], 0.0)],
    )
    def test_mrr(self, ranked, expected):
        assert mrr(ranked) == pytest.approx(expected)

    def test_recall_and_precision_at_k(self):
        assert recall_at_k([1, 0, 1, 0], total_relevant=4, k=4) == pytest.approx(0.5)
        assert precision_at_k([1, 0, 1, 0], k=4) == pytest.approx(0.5)

    def test_aggregate_over_queries(self):
        out = aggregate([[2, 0], [0, 2]], totals=[1, 1], k=2)
        assert out["n"] == 2
        assert 0.0 < out["ndcg@2"] < 1.0
        assert out["mrr"] == pytest.approx(0.75)

    def test_aggregate_handles_empty_input(self):
        assert aggregate([], totals=[], k=5)["n"] == 0


class TestBM25Retriever:
    @pytest.fixture
    def retriever(self) -> BM25Retriever:
        r = BM25Retriever()
        r.index(chunk_resume(RESUME))
        return r

    def test_satisfies_the_protocol(self, retriever):
        assert isinstance(retriever, Retriever)

    def test_lexical_overlap_ranks_first(self, retriever):
        hits = retriever.retrieve("Experience with Kubernetes at scale", k=3)
        assert "Kubernetes" in hits[0].chunk.text

    def test_returns_at_most_k(self, retriever):
        # "at most", not "exactly" -- zero-signal hits are dropped, so a
        # narrow query legitimately returns fewer than k.
        hits = retriever.retrieve("PostgreSQL", k=2)
        assert 1 <= len(hits) <= 2

    def test_ranks_are_sequential_and_scores_descend(self, retriever):
        hits = retriever.retrieve("CI/CD pipeline automation", k=4)
        assert [h.rank for h in hits] == list(range(len(hits)))
        assert all(a.score >= b.score for a, b in zip(hits, hits[1:], strict=False))

    def test_headings_are_not_retrievable(self, retriever):
        from services.matching.chunking import ChunkKind

        hits = retriever.retrieve("PostgreSQL datastore migration", k=5)
        assert hits, "query shares terms with the corpus, expected hits"
        assert all(h.chunk.kind is not ChunkKind.HEADING for h in hits)

    def test_zero_signal_queries_return_nothing(self, retriever):
        assert retriever.retrieve("underwater basket weaving", k=5) == []

    def test_empty_index_returns_nothing(self):
        r = BM25Retriever()
        r.index([])
        assert r.retrieve("anything", k=5) == []

    def test_vocabulary_mismatch_is_the_known_weakness(self, retriever):
        """The failure mode that justifies a dense stage existing at all.

        'container orchestration' shares no terms with 'Kubernetes', so BM25
        cannot rank it first. If this test ever starts passing trivially, the
        gold set has stopped containing paraphrase cases.
        """
        hits = retriever.retrieve("orchestrating containerised workloads", k=5)
        assert hits == [], "BM25 should produce no signal on a pure paraphrase"


class TestRandomRetriever:
    def test_is_deterministic_for_a_given_query(self):
        a, b = RandomRetriever(seed=1), RandomRetriever(seed=1)
        chunks = chunk_resume(RESUME)
        a.index(chunks)
        b.index(chunks)
        q = "Kubernetes experience"
        assert [h.chunk.index for h in a.retrieve(q, 3)] == [
            h.chunk.index for h in b.retrieve(q, 3)
        ]

    def test_different_queries_give_different_orders(self):
        r = RandomRetriever(seed=1)
        r.index(chunk_resume(RESUME))
        assert [h.chunk.index for h in r.retrieve("a", 5)] != [
            h.chunk.index for h in r.retrieve("b", 5)
        ]
