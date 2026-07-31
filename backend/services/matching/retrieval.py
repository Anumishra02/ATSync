"""Retrieval over resume chunks.

Phase 2 stage 1: given a JD requirement, return the resume bullets most
likely to be evidence for it.

`BM25Retriever` exists to be beaten. It is a strong lexical baseline -- in
IR, BM25 routinely beats undertrained dense retrievers, and a dense model
that cannot beat it has earned nothing. Building it first means the
bi-encoder arrives with a number to clear rather than a number to report.

The `Retriever` protocol keeps the eval harness model-agnostic, so
`DenseRetriever` and `HybridRetriever` slot in without touching the harness.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from rank_bm25 import BM25Okapi

from services.matching.chunking import Chunk
from services.skills.normalize import normalize, tokenize


@dataclass(frozen=True, slots=True)
class Hit:
    chunk: Chunk
    score: float
    rank: int


@runtime_checkable
class Retriever(Protocol):
    """Anything that ranks resume chunks against a requirement string."""

    def index(self, chunks: list[Chunk]) -> None: ...

    def retrieve(self, query: str, k: int = 5) -> list[Hit]: ...


def _terms(text: str) -> list[str]:
    """Shared tokenization, so lexical and dense paths see the same text."""
    return [t.text for t in tokenize(normalize(text))]


class BM25Retriever:
    """Okapi BM25 over resume chunks.

    Known weakness, and the reason a dense stage exists at all: BM25 cannot
    match "container orchestration" to a bullet that says "Kubernetes". It
    scores lexical overlap, so vocabulary mismatch is invisible to it. The
    gold set should contain enough paraphrase cases to expose that -- if it
    does not, the set is saturated and the comparison is worthless.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._chunks: list[Chunk] = []
        self._bm25: BM25Okapi | None = None

    def index(self, chunks: list[Chunk]) -> None:
        self._chunks = [c for c in chunks if c.is_scorable]
        corpus = [_terms(c.text) for c in self._chunks]
        # BM25Okapi rejects an empty corpus; keep the retriever usable anyway.
        self._bm25 = BM25Okapi(corpus, k1=self.k1, b=self.b) if corpus else None

    def retrieve(self, query: str, k: int = 5, min_score: float = 1e-9) -> list[Hit]:
        """Rank chunks by BM25, dropping zero-signal hits.

        Without the ``min_score`` floor, a query sharing no terms with any
        chunk still returns a rank-0 hit -- scored 0.0, ordered only by the
        stability of the sort. Downstream that is indistinguishable from a
        confident match, and it silently poisons any aggregate built on
        top-1. An empty list is the honest answer: BM25 has nothing to say
        about this query.
        """
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(_terms(query))
        order = sorted(range(len(scores)), key=lambda i: -scores[i])[:k]
        return [
            Hit(chunk=self._chunks[i], score=float(scores[i]), rank=rank)
            for rank, i in enumerate(order)
            if scores[i] > min_score
        ]


class RandomRetriever:
    """Deterministic shuffle. The floor.

    Every metric should be read against this. An nDCG@5 of 0.55 sounds fine
    until the random baseline scores 0.50 on the same set -- at which point
    the set is too small or too easy, not the system too good.
    """

    def __init__(self, seed: int = 0):
        self.seed = seed
        self._chunks: list[Chunk] = []

    def index(self, chunks: list[Chunk]) -> None:
        self._chunks = [c for c in chunks if c.is_scorable]

    def retrieve(self, query: str, k: int = 5) -> list[Hit]:
        import random

        rng = random.Random(f"{self.seed}:{query}")
        pool = list(self._chunks)
        rng.shuffle(pool)
        return [Hit(chunk=c, score=0.0, rank=i) for i, c in enumerate(pool[:k])]
