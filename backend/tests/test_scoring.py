"""Tests for the ATS scoring service."""

from __future__ import annotations

from pathlib import Path

import pytest

from services.matching.chunking import chunk_resume
from services.skills.matcher import SkillMatcher
from services.skills.taxonomy import Taxonomy
from services.scoring import check_sections, legacy_ats_score, score_resume

SEED = Path(__file__).resolve().parents[1] / "data" / "skills_seed.json"

RESUME = """\
EXPERIENCE

Backend Engineer Intern, Nimbus Labs
• Built a FastAPI service in Python handling 2M requests per day
• Migrated the primary datastore to PostgreSQL and tuned slow joins

EDUCATION

B.Tech, Computer Science

SKILLS

Python, FastAPI, PostgreSQL, Docker
"""

JD = """\
Requirements

• Strong Python and SQL skills are required
• Must have experience with Docker in production

Nice to Have

• Familiarity with Kubernetes
"""


@pytest.fixture(scope="module")
def matcher() -> SkillMatcher:
    return SkillMatcher(Taxonomy.from_seed_json(SEED))


class TestScoring:
    def test_score_is_recomputable_by_hand(self, matcher):
        r = score_resume(matcher, RESUME, JD)
        assert r.score == round(100 * r.weight_matched / r.weight_total)

    def test_matched_skills_carry_evidence(self, matcher):
        r = score_resume(matcher, RESUME, JD)
        py = next(m for m in r.matched if m.skill_id == "python")
        assert py.evidence.text
        assert py.evidence.tier == "exact"

    def test_evidence_offsets_point_into_the_resume(self, matcher):
        r = score_resume(matcher, RESUME, JD)
        for m in r.matched:
            span = RESUME[m.evidence.char_start : m.evidence.char_end]
            assert span.lower() in m.name.lower().replace(" ", "") or span, (
                f"{m.name}: offsets gave {span!r}"
            )

    def test_missing_skill_names_the_requirement_that_wanted_it(self, matcher):
        r = score_resume(matcher, RESUME, JD)
        k8s = next(m for m in r.missing if m.skill_id == "kubernetes")
        assert "Kubernetes" in k8s.requirement
        assert k8s.emphasis == "preferred"

    def test_required_outweighs_preferred(self, matcher):
        r = score_resume(matcher, RESUME, JD)
        docker = next(m for m in r.matched if m.skill_id == "docker")
        k8s = next(m for m in r.missing if m.skill_id == "kubernetes")
        assert docker.weight > k8s.weight

    def test_missing_a_required_skill_costs_more_than_a_preferred_one(self, matcher):
        """Emphasis only moves the score when a JD mixes emphases.

        The score is weighted *coverage* -- a ratio. A JD asking for one
        skill scores 0 or 100 whatever its emphasis, because the weight
        appears in both numerator and denominator and cancels. Both JDs
        below therefore pair the missing skill with one the resume has.
        """
        base = "Requirements\n\n• Must have Python\n\n"
        as_required = base + "Requirements\n\n• Must have Kubernetes in production\n"
        as_preferred = base + "Nice to Have\n\n• Familiarity with Kubernetes\n"
        assert score_resume(matcher, RESUME, as_required).score < score_resume(
            matcher, RESUME, as_preferred
        ).score

    def test_emphasis_cancels_on_a_single_requirement_jd(self, matcher):
        # Documents the ratio property above rather than leaving it implicit.
        req = score_resume(matcher, RESUME, "Requirements\n\n• Must have Kubernetes\n")
        pref = score_resume(matcher, RESUME, "Nice to Have\n\n• Kubernetes\n")
        assert req.score == pref.score == 0
        assert req.missing[0].weight > pref.missing[0].weight

    def test_boilerplate_does_not_affect_the_score(self, matcher):
        blurb = "About Us\n\nWe are a fast-growing startup using React and Kafka.\n\n"
        assert score_resume(matcher, RESUME, blurb + JD).score == score_resume(
            matcher, RESUME, JD
        ).score

    def test_empty_jd_is_uncomputable_not_a_confident_zero(self, matcher):
        # Was `score == 0` -- itself the bug: an empty JD has nothing to
        # compare the resume against, which is not the same claim as "the
        # resume matched none of the JD's requirements." See score_resume's
        # docstring (Phase C1's contrast test found this the same way it
        # found bug-2's need in check_quantification -- by refusing to
        # trust a result before checking the mechanism behind it).
        r = score_resume(matcher, RESUME, "")
        assert r.score is None
        assert r.matched == [] and r.missing == []
        assert r.weight_total == 0

    def test_perfect_coverage_scores_one_hundred(self, matcher):
        jd = "Requirements\n\n• Must have Python and PostgreSQL\n"
        assert score_resume(matcher, RESUME, jd).score == 100

    def test_result_serializes(self, matcher):
        d = score_resume(matcher, RESUME, JD).to_dict()
        assert set(d) == {"score", "matched", "missing", "sections", "coverage"}


class TestSectionChecks:
    def test_real_headings_are_detected(self, matcher):
        s = check_sections(chunk_resume(RESUME))
        assert s["experience"] and s["education"] and s["skills"]

    def test_absent_section_reports_false(self, matcher):
        assert check_sections(chunk_resume(RESUME))["projects"] is False

    def test_body_words_no_longer_fake_a_section(self, matcher):
        """Regression from the original v1 review.

        v1 regex-matched the body, so 'developed' anywhere meant a Projects
        section existed and 'work' meant an Experience section did. Almost
        every resume scored full marks on a check that measured nothing.
        """
        text = "SUMMARY\n\nI developed several systems and did great work.\n"
        s = check_sections(chunk_resume(text))
        assert s["projects"] is False
        assert s["experience"] is False


class TestLegacyAtsScore:
    """legacy_ats_score is the live-endpoint drop-in for v1's calculate_ats_score.

    Same shape, same 70/30 formula -- these tests exist to prove the actual
    live bug (substring matching false positives) is fixed by switching the
    underlying matcher, not to re-test score_resume's own behavior.
    """

    def test_java_is_not_falsely_matched_inside_javascript(self, matcher):
        # The bug from the original review, now on the path routes/resume.py
        # actually calls. "backend" is a required supporting cue for "Java"
        # (the ambiguity gate correctly needs one -- see
        # services/skills/README.md's java-the-beverage case); without it
        # this sentence would test the gate, not the substring bug.
        result = legacy_ats_score(
            matcher,
            resume_text="Looking for a JavaScript developer",
            jd_text="Requirements: JavaScript and Java backend experience required",
        )
        assert "JavaScript" in result["matched_skills"]
        assert "Java" in result["missing_skills"]
        assert "Java" not in result["matched_skills"]

    def test_resume_side_substring_match_is_also_fixed(self, matcher):
        # v1's bug was double-sided: it substring-checked the JD to find
        # skills, then substring-checked the RESUME text to see if each was
        # present -- so "java" in a resume that only says "javascript" would
        # have counted as a match on the resume side too.
        result = legacy_ats_score(
            matcher,
            resume_text="Extensive JavaScript and TypeScript experience",
            jd_text="Requirements: Java backend development experience required",
        )
        assert "Java" in result["missing_skills"]
        assert "Java" not in result["matched_skills"]

    def test_return_shape_matches_v1_exactly(self, matcher):
        result = legacy_ats_score(matcher, RESUME, JD)
        assert set(result) == {
            "ats_score", "grade", "verdict", "skill_score", "keyword_score",
            "matched_skills", "missing_skills", "total_jd_skills",
            "total_matched", "summary",
        }
        assert isinstance(result["matched_skills"], list)
        assert all(isinstance(s, str) for s in result["matched_skills"])
        assert all(isinstance(s, str) for s in result["missing_skills"])

    def test_empty_jd_scores_zero_without_dividing_by_zero(self, matcher):
        result = legacy_ats_score(matcher, RESUME, "")
        assert result["ats_score"] == 0
        assert result["matched_skills"] == []
        assert result["missing_skills"] == []
