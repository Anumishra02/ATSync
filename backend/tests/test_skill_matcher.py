"""Tests for the skill extraction cascade.

The first class is the important one: every test in it is a bug that shipped
in ATSync v1 and silently inflated user scores.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from services.skills.matcher import SkillMatcher
from services.skills.models import MatchTier
from services.skills.taxonomy import Taxonomy

SEED = Path(__file__).resolve().parents[1] / "data" / "skills_seed.json"


@pytest.fixture(scope="module")
def taxonomy() -> Taxonomy:
    return Taxonomy.from_seed_json(SEED)


@pytest.fixture(scope="module")
def matcher(taxonomy: Taxonomy) -> SkillMatcher:
    return SkillMatcher(taxonomy)


def ids(matcher: SkillMatcher, text: str) -> set[str]:
    return matcher.extract(text).skill_ids


# ---------------------------------------------------------------------------
# Regressions from v1
# ---------------------------------------------------------------------------


class TestV1Regressions:
    def test_java_is_not_found_inside_javascript(self, matcher):
        found = ids(matcher, "Looking for a JavaScript developer")
        assert "javascript" in found
        assert "java" not in found

    def test_oop_is_not_found_inside_loops(self, matcher):
        found = ids(matcher, "Comfortable writing loops and recursion")
        assert "oop" not in found

    def test_go_is_not_found_inside_ordinary_prose(self, matcher):
        found = ids(matcher, "Helped the organisation go to market faster")
        assert "go" not in found

    def test_restful_apis_resolves_to_one_canonical_skill(self, matcher):
        for phrasing in ["RESTful APIs", "RESTful API", "REST APIs", "REST API"]:
            assert ids(matcher, phrasing) == {"rest-api"}, phrasing

    def test_object_oriented_programming_hyphen_variants_unify(self, matcher):
        assert ids(matcher, "Object-Oriented Programming") == {"oop"}
        assert ids(matcher, "object oriented programming") == {"oop"}
        assert ids(matcher, "OOP") == {"oop"}


# ---------------------------------------------------------------------------
# Tokenization edge cases
# ---------------------------------------------------------------------------


class TestTokenization:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("Proficient in C++ and C#.", {"cpp", "csharp"}),
            ("Built with Node.js.", {"nodejs"}),
            ("Owned the CI/CD pipeline", {"cicd"}),
            ("Shipped a Next.js frontend", {"nextjs"}),
            ("Used scikit-learn heavily", {"scikit-learn"}),
        ],
    )
    def test_punctuation_heavy_terms(self, matcher, text, expected):
        assert expected <= ids(matcher, text)

    def test_longest_ngram_wins(self, matcher):
        result = matcher.extract("Strong machine learning background")
        assert result.skill_ids == {"machine-learning"}

    def test_case_and_unicode_dashes(self, matcher):
        # en-dash, as emitted by many PDF exporters
        assert ids(matcher, "OBJECT–ORIENTED PROGRAMMING") == {"oop"}

    def test_spans_point_at_the_original_text(self, matcher):
        text = "We need someone strong in Kubernetes for this role"
        match = next(iter(matcher.extract(text).matches))
        assert text.lower()[match.char_start : match.char_end] == "kubernetes"


# ---------------------------------------------------------------------------
# Fuzzy tier
# ---------------------------------------------------------------------------


class TestFuzzyTier:
    @pytest.mark.parametrize(
        ("typo", "expected"),
        [
            ("kubernetres", "kubernetes"),
            ("postgresql databse work", "postgresql"),
            ("javascrpt", "javascript"),
        ],
    )
    def test_typos_are_recovered(self, matcher, typo, expected):
        assert expected in ids(matcher, typo)

    def test_fuzzy_matches_are_tagged_as_fuzzy(self, matcher):
        matches = matcher.extract("kubernetres").matches
        assert matches and matches[0].tier is MatchTier.FUZZY
        assert matches[0].confidence < 1.0

    def test_common_prose_does_not_fuzzy_match(self, matcher):
        prose = (
            "Worked closely with other teams during the year to deliver "
            "results for many clients across several projects"
        )
        assert ids(matcher, prose) == set()


# ---------------------------------------------------------------------------
# Result aggregation
# ---------------------------------------------------------------------------


class TestExtractionResult:
    def test_repeated_skill_deduplicates_to_best_match(self, matcher):
        result = matcher.extract("Python. Python again. And more Python.")
        assert result.skill_ids == {"python"}
        assert len(result.best_per_skill()) == 1

    def test_tier_counts_are_reported(self, matcher):
        result = matcher.extract("Python, kubernetres, and FastAPI")
        counts = result.tier_counts()
        assert counts["exact"] == 2
        assert counts["fuzzy"] == 1


# ---------------------------------------------------------------------------
# Ambiguity gate
# ---------------------------------------------------------------------------


class TestAmbiguityGate:
    @pytest.mark.parametrize(
        "prose",
        [
            "Helped the organisation go to market faster",
            "Encouraged the team to go above and beyond",
            "Continued to excel across every review cycle",
        ],
    )
    def test_common_verb_usage_is_rejected(self, matcher, prose):
        assert ids(matcher, prose) & {"go", "excel"} == set()

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("Built backend microservices in Go", "go"),
            ("Go and Rust for systems programming", "go"),
            ("Golang microservices at scale", "go"),
            ("Advanced Excel: pivot tables and macros", "excel"),
            ("Ran ETL jobs on Apache Spark clusters", "spark"),
        ],
    )
    def test_supported_usage_is_accepted(self, matcher, text, expected):
        assert expected in ids(matcher, text)

    def test_unambiguous_alias_bypasses_the_gate(self, matcher):
        # "Golang" needs no supporting context -- the word itself is proof.
        assert "go" in ids(matcher, "Golang")

    def test_java_the_beverage_is_rejected(self, matcher):
        # Found by the adversarial semantic gold set, not by reading the code.
        assert "java" not in ids(matcher, "Brewed java for the team every morning")

    def test_java_the_language_is_accepted(self, matcher):
        assert "java" in ids(matcher, "Java and Spring Boot for backend services")
