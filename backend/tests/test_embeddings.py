"""Smoke test for the real sentence-transformers encoder.

Downloads BAAI/bge-small-en-v1.5 (~130MB) on first run and is excluded from
the default test run (see pytest.ini) -- run explicitly with `pytest -m slow`.

`SentenceTransformerEncoder` is not wired into `SkillMatcher` (tier 3 was
built, measured, and cut -- see services/skills/README.md). This test
covers the encoder standalone, which is what Phase 2 will actually reuse.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def encoder():
    # Imported lazily, inside the fixture body, so a plain `pytest` run
    # (which deselects `slow` tests) never pays the torch import cost --
    # deselected tests' fixtures never execute, but a module-level import
    # in this file would run during collection regardless of selection.
    from services.skills.embeddings import SentenceTransformerEncoder

    return SentenceTransformerEncoder()


def test_encoder_produces_unit_norm_vectors(encoder):
    vecs = encoder.encode(["kubernetes", "container orchestration"])
    assert len(vecs) == 2
    for v in vecs:
        norm = sum(x * x for x in v) ** 0.5
        assert abs(norm - 1.0) < 1e-3
