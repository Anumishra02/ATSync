"""Tests for the Phase 2 gold set loader and annotator agreement."""

from __future__ import annotations

import json

import pytest

from evaluation.gold import (
    Judgement,
    Pair,
    agreement_report,
    load_gold,
    weighted_kappa,
)

EXAMPLE = "evaluation/gold_retrieval_example.json"


class TestGoldLoading:
    def test_example_loads_and_validates(self):
        pairs = load_gold(EXAMPLE)
        assert len(pairs) == 1
        assert pairs[0].validate() == []

    def test_requirements_and_evidence_resolve_to_chunks(self):
        pair = load_gold(EXAMPLE)[0]
        req_texts = {c.text for c in pair.requirements}
        ev_texts = {c.text for c in pair.resume_chunks}
        for j in pair.judgements:
            assert j.requirement in req_texts
            assert j.evidence in ev_texts

    def test_chunker_drift_is_a_loud_failure(self, tmp_path):
        """A labelled string that no longer chunks the same way must raise.

        Silently re-pointing human judgements at different bullets would
        produce a confident, wrong number -- the worst failure mode available.
        """
        data = json.loads(open(EXAMPLE, encoding="utf-8").read())
        data["pairs"][0]["judgements"][0]["evidence"] = "a bullet that does not exist"
        p = tmp_path / "drifted.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(ValueError, match="no longer matches"):
            load_gold(p)

    def test_non_strict_mode_tolerates_drift(self, tmp_path):
        data = json.loads(open(EXAMPLE, encoding="utf-8").read())
        data["pairs"][0]["judgements"][0]["evidence"] = "nope"
        p = tmp_path / "drifted.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        assert len(load_gold(p, strict=False)) == 1

    def test_unjudged_pairs_score_zero(self):
        pair = load_gold(EXAMPLE)[0]
        req = pair.requirements[0].text
        rel = pair.relevance_for(req, ["a bullet nobody labelled"])
        assert rel == [0.0]


class TestWeightedKappa:
    def test_perfect_agreement(self):
        assert weighted_kappa([0, 1, 2, 1], [0, 1, 2, 1]) == pytest.approx(1.0)

    def test_ordinal_weighting_penalises_distance(self):
        """2-vs-0 must cost more than 2-vs-1. Unweighted kappa cannot see this."""
        near = weighted_kappa([2, 2, 0, 0, 1, 1], [1, 2, 0, 0, 1, 1])
        far = weighted_kappa([2, 2, 0, 0, 1, 1], [0, 2, 0, 0, 1, 1])
        assert far < near

    def test_disagreement_lowers_kappa(self):
        assert weighted_kappa([0, 0, 2, 2], [2, 2, 0, 0]) < 0.0

    def test_degenerate_constant_labels(self):
        # Both annotators said 1 everywhere: no information, not agreement.
        assert weighted_kappa([1, 1, 1], [1, 1, 1]) == 1.0

    def test_mismatched_lengths_raise(self):
        with pytest.raises(ValueError):
            weighted_kappa([0, 1], [0])

    def test_empty_input(self):
        assert weighted_kappa([], []) == 0.0


class TestAgreementReport:
    def _pair(self, annotator: str, grades: list[int]) -> Pair:
        return Pair(
            id="p1", resume_text="", jd_text="", annotator=annotator,
            judgements=[
                Judgement(requirement=f"r{i}", evidence=f"e{i}", grade=g)
                for i, g in enumerate(grades)
            ],
        )

    def test_aligns_shared_judgements_only(self):
        a = self._pair("a", [2, 1, 0])
        b = self._pair("b", [2, 1])
        rep = agreement_report([a], [b])
        assert rep["n"] == 2
        assert rep["only_a"] == 1
        assert rep["only_b"] == 0

    def test_disagreements_sorted_by_severity(self):
        a = self._pair("a", [2, 2])
        b = self._pair("b", [1, 0])
        rep = agreement_report([a], [b])
        # the 2-vs-0 must come before the 2-vs-1
        assert abs(rep["disagreements"][0]["a"] - rep["disagreements"][0]["b"]) == 2

    def test_no_overlap_returns_zero_not_error(self):
        a = self._pair("a", [2])
        b = Pair(id="p2", resume_text="", jd_text="", judgements=[])
        assert agreement_report([a], [b])["n"] == 0
