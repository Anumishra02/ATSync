"""Tests for the dual-mode (quality / match) analysis pipeline.

The core claims under test: a scorer whose requires_jd is True is never
even invoked when there's no JD (not called-and-discarded); uncomputable
and not_applicable dimensions are excluded from available_points, not
silently treated as 0; the /100 display score is only renormalized in
quality mode, never in match mode (where available_points is always 100
by construction).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from services.analysis.models import AnalysisResult, DimensionResult
from services.analysis.pipeline import run_analysis
from services.analysis.scorers import (
    AchievementsScorer,
    ExperienceScorer,
    RelevanceScorer,
    SkillsScorer,
    StructureScorer,
    WritingScorer,
)
from services.skills.matcher import SkillMatcher
from services.skills.taxonomy import Taxonomy

SEED = Path(__file__).resolve().parents[1] / "data" / "skills_seed.json"

RESUME = """\
Backend Engineer Intern, Nimbus Labs
June 2025 - Aug 2025

Experience

- Built a FastAPI service in Python handling 2M requests per day
- Migrated the primary datastore to PostgreSQL, cutting query time by 40%
- Deployed the service on Docker across three regions
- Wrote the CI/CD pipeline on GitHub Actions with automated tests

Education

B.Tech, Computer Science

Skills

Python, FastAPI, PostgreSQL, Docker, Git, AWS

Certifications

AWS Certified Cloud Practitioner
"""

JD = """\
Requirements

- Strong Python and PostgreSQL skills are required
- Must have experience with Docker in production

Nice to Have

- Familiarity with Kubernetes
"""

PROSE_ONLY_RESUME = """\
Experience

Acme Corp, Analyst, 2023-2024

Developed and implemented a streamlined process for gathering
requirements, reducing delivery time by 15 percent through close
collaboration with cross-functional teams.

Education

B.A. in Communications
"""

NO_EXPERIENCE_RESUME = """\
Skills

Python, SQL

Education

B.A. in Economics
"""


@pytest.fixture(scope="module")
def matcher() -> SkillMatcher:
    return SkillMatcher(Taxonomy.from_seed_json(SEED))


class TestDimensionResultInvariant:
    def test_scored_requires_a_score(self):
        with pytest.raises(ValueError):
            DimensionResult(dimension="x", score=None, max_points=10, status="scored")

    def test_non_scored_forbids_a_score(self):
        with pytest.raises(ValueError):
            DimensionResult(dimension="x", score=5, max_points=10, status="not_applicable")

    def test_uncomputable_is_constructible(self):
        d = DimensionResult(dimension="x", score=None, max_points=10, status="uncomputable")
        assert d.score is None


class TestAnalysisResultAggregation:
    def test_available_points_excludes_non_scored_dimensions(self):
        result = AnalysisResult(mode="quality", dimensions=[
            DimensionResult("a", 10, 15, "scored"),
            DimensionResult("b", None, 20, "uncomputable"),
            DimensionResult("c", None, 15, "not_applicable"),
        ])
        assert result.available_points == 15

    def test_normalization_matches_the_worked_example(self):
        # The exact worked example from the Phase 0 spec's Step 0.6/0.7:
        # 13+12+11+15+14 = 65 out of 15+15+15+20+20 = 85 -> 76 (rounded).
        result = AnalysisResult(mode="quality", dimensions=[
            DimensionResult("structure", 13, 15, "scored"),
            DimensionResult("writing", 12, 15, "scored"),
            DimensionResult("achievements", 11, 15, "scored"),
            DimensionResult("skills", 15, 20, "scored"),
            DimensionResult("experience", 14, 20, "scored"),
            DimensionResult("relevance", None, 15, "not_applicable"),
        ])
        assert result.available_points == 85
        assert result.raw_score == 65
        assert result.score == 76

    def test_match_mode_needs_no_renormalization(self):
        # Step 0.8's worked example: every dimension scored, sums to
        # exactly 100 available points, so raw_score == score.
        result = AnalysisResult(mode="match", dimensions=[
            DimensionResult("structure", 13, 15, "scored"),
            DimensionResult("writing", 12, 15, "scored"),
            DimensionResult("achievements", 16, 20, "scored"),
            DimensionResult("skills", 12, 15, "scored"),
            DimensionResult("experience", 14, 20, "scored"),
            DimensionResult("relevance", 12, 15, "scored"),
        ])
        assert result.available_points == 100
        assert result.raw_score == 79
        assert result.score == 79

    def test_zero_available_points_does_not_divide_by_zero(self):
        result = AnalysisResult(mode="quality", dimensions=[
            DimensionResult("a", None, 15, "uncomputable"),
        ])
        assert result.available_points == 0
        assert result.score == 0


class TestRequiresJdGating:
    def test_relevance_is_never_invoked_without_a_jd(self, matcher):
        class ExplodesIfCalled:
            name = "relevance"
            max_points = 15.0
            requires_jd = True

            def score(self, resume_text, jd_text, matcher):
                raise AssertionError("requires_jd scorer must not be called when jd_text is None")

        result = run_analysis(RESUME, None, matcher, scorers=(ExplodesIfCalled(),))
        assert result.dimensions[0].status == "not_applicable"

    def test_quality_mode_runs_five_dimensions_match_mode_runs_six(self, matcher):
        quality = run_analysis(RESUME, None, matcher)
        match = run_analysis(RESUME, JD, matcher)

        assert quality.mode == "quality"
        assert match.mode == "match"
        assert {d.dimension for d in quality.scored} == {
            "structure", "writing", "achievements", "skills", "experience",
        }
        assert {d.dimension for d in match.scored} == {
            "structure", "writing", "achievements", "skills", "experience", "relevance",
        }
        assert quality.available_points == 85  # 100 - relevance's 15
        assert match.available_points == 100


class TestEndToEndRealResume:
    def test_quality_mode_scores_a_real_resume(self, matcher):
        result = run_analysis(RESUME, None, matcher)
        assert result.mode == "quality"
        assert 0 <= result.score <= 100
        relevance = next(d for d in result.dimensions if d.dimension == "relevance")
        assert relevance.status == "not_applicable"

    def test_match_mode_scores_a_real_resume_against_a_real_jd(self, matcher):
        result = run_analysis(RESUME, JD, matcher)
        relevance = next(d for d in result.dimensions if d.dimension == "relevance")
        assert relevance.status == "scored"
        assert relevance.score > 0  # Python/Docker/PostgreSQL genuinely match

    def test_achievements_uncomputable_on_a_prose_only_resume(self, matcher):
        result = run_analysis(PROSE_ONLY_RESUME, None, matcher)
        achievements = next(d for d in result.dimensions if d.dimension == "achievements")
        assert achievements.status == "uncomputable"
        # uncomputable must not shrink available_points to a fake full 100 --
        # 85 - achievements' 20 = 65 possible from the other four dimensions.
        assert result.available_points == 65

    def test_experience_uncomputable_when_no_experience_section_exists(self, matcher):
        result = run_analysis(NO_EXPERIENCE_RESUME, None, matcher)
        experience = next(d for d in result.dimensions if d.dimension == "experience")
        assert experience.status == "uncomputable"


class TestSkillsScorerDualMode:
    def test_without_jd_counts_recognized_skills(self, matcher):
        d = SkillsScorer().score(RESUME, None, matcher)
        assert d.status == "scored"
        assert d.detail["mode"] == "count"
        assert d.detail["skills_found"] >= 5  # python, fastapi, postgresql, docker, git, aws

    def test_with_jd_measures_match_rate_against_jd_skills(self, matcher):
        d = SkillsScorer().score(RESUME, JD, matcher)
        assert d.status == "scored"
        assert d.detail["mode"] == "jd_match"
        # python, postgresql, docker are all named in the JD and present
        assert d.detail["matched"] >= 2

    def test_jd_with_no_recognized_skills_is_uncomputable_not_zero(self, matcher):
        d = SkillsScorer().score(RESUME, "We are looking for a great team player.", matcher)
        assert d.status == "uncomputable"


class TestOtherScorersStandalone:
    def test_structure_scorer_on_real_resume(self, matcher):
        d = StructureScorer().score(RESUME, None, matcher)
        assert d.status == "scored"
        assert d.detail["sections"]["experience"] is True
        assert d.detail["sections"]["skills"] is True

    def test_writing_scorer_runs_without_a_jd(self, matcher):
        d = WritingScorer().score(RESUME, None, matcher)
        assert d.status == "scored"

    def test_achievements_scorer_on_real_resume(self, matcher):
        d = AchievementsScorer().score(RESUME, None, matcher)
        assert d.status == "scored"
        assert d.detail["quantified"] >= 1  # "2M requests", "40%" bullets

    def test_experience_scorer_rewards_entry_completeness(self, matcher):
        # Phase 1 item 1: this dimension checks the rubric's own mechanical
        # fields (org, title, city/state, dates) per entry, not bullet
        # volume -- see ExperienceScorer's docstring for why the previous
        # bullet-count proxy was replaced outright.
        complete = ExperienceScorer().score(
            "Experience\n\n"
            "Acme Corp, San Francisco, CA\n"
            "Backend Engineer June 2023 - Present\n\n"
            "- Built a FastAPI service handling 2M requests per day\n"
            "- Migrated the datastore to PostgreSQL\n",
            None, matcher,
        )
        incomplete = ExperienceScorer().score(
            "Experience\n\nAcme Corp\n\n- Built a FastAPI service handling 2M requests per day\n",
            None, matcher,
        )
        assert complete.status == "scored" and incomplete.status == "scored"
        assert complete.score > incomplete.score
        # A fully-specified single entry should reach the max -- the
        # "points per satisfied criterion" ceiling check from Phase 1
        # item 3 applies here just as much as it did to Achievements.
        assert complete.score == complete.max_points

    def test_relevance_scorer_not_applicable_without_jd(self, matcher):
        d = RelevanceScorer().score(RESUME, None, matcher)
        assert d.status == "not_applicable"
        assert d.score is None
