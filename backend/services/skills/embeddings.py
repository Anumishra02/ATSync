"""Real embedding encoder, backed by sentence-transformers.

Not wired into matcher.py -- tier 3 (embedding-cosine semantic matching)
was built, measured against evaluation/gold_semantic.json, and cut (see
services/skills/README.md, "What I removed, and why"). Kept because Phase 2
(bi-encoder retrieval over whole resume bullets) will want a real encoder
again. Importing this module pulls in torch; nothing else in services/skills
does, by design, so the fast test suite stays fast.
"""

from __future__ import annotations

from sentence_transformers import SentenceTransformer

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"


class SentenceTransformerEncoder:
    """Turns text into unit-norm embedding vectors.

    Normalizes embeddings so a plain dot product between two vectors is
    cosine similarity.
    """

    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return vectors.tolist()
