"""Tests for HybridSkillMatcher (services/skills/hybrid_matcher.py) --
Phase B: the fallback hybrid for JD-match mode only.

Uses a lightweight fake ESCO extractor throughout, not esco-skill-extractor
itself -- these tests must stay fast and network-free (backend/data/README.md's
CI rule), and they're testing the FALLBACK WIRING, not embedding quality
(that's Phase A/tune_esco_threshold.py's job, already done against the
real library). The fake's `.extract()` matches the same `set[str]` contract
EscoEmbedExtractor.extract() returns.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from services.matching.chunking import normalize_document_text
from services.scoring import score_resume
from services.skills.hybrid_matcher import HybridSkillMatcher, _EscoTaxonomyProxy
from services.skills.matcher import SkillMatcher
from services.skills.taxonomy import Taxonomy

SEED = Path(__file__).resolve().parents[1] / "data" / "skills_seed.json"

RESUME = """\
Experience
- Coordinated stakeholder communications across three regional offices
- Managed budget reconciliation for the annual conference
"""


@pytest.fixture(scope="module")
def seed_matcher() -> SkillMatcher:
    return SkillMatcher(Taxonomy.from_seed_json(SEED))


class FakeEscoExtractor:
    """Deterministic stand-in for EscoEmbedExtractor. `hits` maps a
    substring to the ESCO URI it "finds" when that substring appears in
    the queried text -- crude, but exactly what's needed to test fallback
    wiring without a real embedding model.
    """

    def __init__(self, hits: dict[str, str], calls: list[str] | None = None):
        self._hits = hits
        self.calls = calls if calls is not None else []

    def extract(self, text: str) -> set[str]:
        self.calls.append(text)
        low = text.lower()
        return {f"esco:{uri}" for needle, uri in self._hits.items() if needle in low}


def _labels(*pairs: tuple[str, str]) -> dict[str, str]:
    return dict(pairs)


class TestForJdDecision:
    def test_seed_success_never_touches_esco_factory(self, seed_matcher):
        # A JD the seed taxonomy can read (Python is a seed skill) must
        # never construct the ESCO extractor at all -- that's the whole
        # point of "lazy": no needless embedding build when seed suffices.
        def exploding_factory():
            raise AssertionError("ESCO factory called even though seed found a skill")

        jd_text = normalize_document_text("Requirements\n- Strong Python skills\n")
        m = HybridSkillMatcher.for_jd(seed_matcher, exploding_factory, {}, jd_text)
        assert m.use_esco is False
        # Exercise .extract() too -- confirms the factory really is never invoked.
        m.extract(jd_text)

    def test_seed_empty_falls_back_to_esco(self, seed_matcher):
        # A JD with real content the seed taxonomy has no vocabulary for
        # (stakeholder coordination, budget reconciliation -- no seed skill
        # names either) must trigger the fallback.
        jd_text = normalize_document_text(
            "Requirements\n- Manage stakeholder communications\n- Reconcile budgets\n"
        )
        assert not seed_matcher.extract(jd_text).skill_ids  # sanity: seed genuinely finds nothing here

        fake = FakeEscoExtractor({"stakeholder": "uri-stakeholder", "budget": "uri-budget"})
        m = HybridSkillMatcher.for_jd(seed_matcher, lambda: fake, _labels(("uri-stakeholder", "Stakeholder Management")), jd_text)
        assert m.use_esco is True

        result = m.extract(jd_text)
        assert result.skill_ids == {"esco:uri-stakeholder", "esco:uri-budget"}
        match = next(x for x in result.matches if x.skill.id == "esco:uri-stakeholder")
        assert match.skill.canonical == "Stakeholder Management"  # resolved via the label lookup
        assert match.tier.value == "semantic"


class TestBothLayersEmpty:
    """The path explicitly asked for: neither seed nor the fallback finds
    anything. None of the 33 real JDs in the eval corpus produce this
    (ESCO at t=0.55 covered all 20 of seed's zero-skill JDs) -- so it's
    tested synthetically here, not skipped for lack of a real example.
    """

    def test_esco_fallback_also_empty_yields_no_matches(self, seed_matcher):
        jd_text = normalize_document_text("Requirements\n- Be a good team player\n")
        assert not seed_matcher.extract(jd_text).skill_ids

        fake = FakeEscoExtractor({})  # finds nothing, deliberately -- both layers empty
        m = HybridSkillMatcher.for_jd(seed_matcher, lambda: fake, {}, jd_text)
        assert m.use_esco is True
        result = m.extract(jd_text)
        assert result.skill_ids == set()
        assert result.matches == []

    def test_score_resume_returns_uncomputable_not_a_confident_zero(self, seed_matcher):
        # The actual bug this cycle found and fixed: score_resume must
        # return score=None here, not 0 -- there is nothing to compare the
        # resume against, which is a different claim than "matched nothing."
        jd_text = normalize_document_text("Requirements\n- Be a good team player\n")
        fake = FakeEscoExtractor({})
        m = HybridSkillMatcher.for_jd(seed_matcher, lambda: fake, {}, jd_text)

        result = score_resume(m, normalize_document_text(RESUME), jd_text)
        assert result.score is None
        assert result.weight_total == 0
        assert result.matched == [] and result.missing == []


class TestTaxonomyProxy:
    def test_resolves_a_missing_esco_skill_by_uri(self):
        # The gap found by reading score_resume before shipping this: a
        # skill required by the JD but absent from the resume ("missing")
        # is named via matcher.taxonomy.get(skill_id), never populated in
        # `names` (which only comes from resume matches). Without this
        # proxy, that call crashes on HybridSkillMatcher.
        proxy = _EscoTaxonomyProxy({"uri-x": "Some ESCO Skill"})
        skill = proxy.get("esco:uri-x")
        assert skill is not None
        assert skill.canonical == "Some ESCO Skill"
        assert proxy.get("esco:unknown-uri") is None

    def test_score_resume_names_a_missing_esco_skill_without_crashing(self, seed_matcher):
        jd_text = normalize_document_text("Requirements\n- Manage stakeholder communications\n")
        assert not seed_matcher.extract(jd_text).skill_ids

        # Resume has no overlap at all -- forces a "missing" entry, which
        # is exactly the code path that used to crash under the hybrid.
        fake = FakeEscoExtractor({"stakeholder": "uri-stakeholder"})
        m = HybridSkillMatcher.for_jd(
            seed_matcher, lambda: fake, _labels(("uri-stakeholder", "Stakeholder Management")), jd_text
        )
        result = score_resume(m, normalize_document_text("Experience\n- Wrote unit tests\n"), jd_text)
        assert result.score == 0  # a real zero: the JD had a requirement, the resume just lacks it
        missing = next(x for x in result.missing if x.skill_id == "esco:uri-stakeholder")
        assert missing.name == "Stakeholder Management"
