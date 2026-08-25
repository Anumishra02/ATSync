"""Defect-injection regression suite: does a known-direction degradation
actually lower the score of the dimension it should?

10 real resumes (from the committed evaluation/step0/Resumes/ corpus --
not test_corpus/, which stays local-only) x 4 known-direction
degradations = 40 comparisons, no labeling required. Ground truth is the
direction, not a target number: strip the numbers out of a bullet and its
achievements score must fall; make bullets passive/repetitive/filler-laden
and writing score must fall. If a dimension's score does NOT fall, that
dimension's proxy isn't discriminating and needs rewriting, not
recalibrating -- this is exactly the test that found WritingScorer's old
word-repetition-only proxy blind to passive voice and filler (three
synthetic examples scored identically, 15.0/15.0/15.0, before the
rewrite -- see WritingScorer's docstring).

This is meant to run in CI permanently: no external corpus dependency
beyond what's already committed, no human labels, no network calls.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from services.analysis.scorers import AchievementsScorer, WritingScorer
from services.matching.chunking import BULLET, normalize_document_text
from services.parsing.pdf_extract import extract_document
from services.skills.matcher import SkillMatcher
from services.skills.taxonomy import Taxonomy

SEED = Path(__file__).resolve().parents[1] / "data" / "skills_seed.json"
RESUMES_DIR = Path(__file__).resolve().parents[2] / "evaluation" / "step0" / "Resumes"

# 10 resumes confirmed (see the calibration pass in the Experience scorer's
# commit) to have substantial real bullet content -- a degradation test on
# a bullet-free resume couldn't show anything degrading.
RESUME_IDS = ["R07", "R16", "R19", "R21", "R22", "R25", "R33", "R36", "R37", "R38"]


# ---------------------------------------------------------------------------
# Degradation injectors -- each takes real bullet-bearing resume text and
# damages ONE specific property, deliberately and deterministically.
# ---------------------------------------------------------------------------


def strip_quantification(text: str) -> str:
    """Remove every digit sequence, so no bullet can be detected as
    quantified by check_quantification's r'\\d+' test.
    """
    return re.sub(r"\d+", "", text)


def _inject_after_bullet(text: str, insertion: str) -> str:
    """Insert `insertion` immediately after the bullet marker on every
    line BULLET recognizes as one.

    Reuses chunking.py's own bullet regex directly, rather than a
    hand-copied approximation of it -- an earlier version of this file
    used its own narrower "[bullet-dash-star]" pattern and silently
    matched zero lines on any resume using a glyph outside that set (e.g.
    "●", a real bullet character several corpus resumes use, which
    chunking.py's BULLET already recognized). Importing the real pattern
    means this can't drift out of sync with it again.
    """
    out_lines = []
    for line in text.splitlines(keepends=True):
        m = BULLET.match(line)
        out_lines.append(line[: m.end()] + insertion + line[m.end():] if m else line)
    return "".join(out_lines)


def inject_passive_voice(text: str) -> str:
    """Insert a guaranteed passive-voice construction into every bullet
    line, deterministically matching WritingScorer's _PASSIVE_PATTERN
    regardless of the bullet's own original content.

    Deliberately ends in a period, not a colon: an earlier version used
    "This work was completed: " and every injected line was silently
    dropped from scoring entirely once WritingScorer started excluding
    FACT_LISTING_PATTERN lines (Phase 1 item 1 follow-up) -- the phrase's
    own "label: " shape collided with the exact pattern meant to catch
    "Coursework: ..."-style fact listings, a coincidence specific to this
    injector's wording, not something a real resume's fact-listing lines
    would trigger (those are 1-3 word labels, not full sentences).
    """
    return _inject_after_bullet(text, "This task was completed. ")


def inject_repetition(text: str) -> str:
    """Insert the same generic (non-skill, non-stopword) word into every
    bullet line, five times over, to trigger the repeated-word penalty
    regardless of the resume's own vocabulary.
    """
    return _inject_after_bullet(text, "wombat wombat wombat wombat wombat ")


def add_filler(text: str) -> str:
    """Insert a guaranteed filler phrase into every bullet line."""
    return _inject_after_bullet(text, "Was basically responsible for helping with: ")


@pytest.fixture(scope="module")
def matcher() -> SkillMatcher:
    return SkillMatcher(Taxonomy.from_seed_json(SEED))


@pytest.fixture(scope="module")
def resumes() -> dict[str, str]:
    out = {}
    for rid in RESUME_IDS:
        result = extract_document(RESUMES_DIR / f"{rid}.pdf")
        out[rid] = normalize_document_text(result.text)
    return out


class TestQuantificationStrippingLowersAchievements:
    @pytest.mark.parametrize("resume_id", RESUME_IDS)
    def test_strip_quantification_lowers_achievements_score(self, resume_id, resumes, matcher):
        base = AchievementsScorer().score(resumes[resume_id], None, matcher)
        degraded = AchievementsScorer().score(strip_quantification(resumes[resume_id]), None, matcher)
        assert base.status == "scored", f"{resume_id}: base achievements should be scored"
        # Degraded may legitimately become uncomputable if every bullet's
        # ONLY content was a number -- that's a valid outcome (0 real
        # bullets left to grade), not a test failure, but it must not
        # score HIGHER than the base.
        if degraded.status == "scored":
            assert degraded.score < base.score, f"{resume_id}: {degraded.score} !< {base.score}"


class TestPassiveVoiceLowersWriting:
    @pytest.mark.parametrize("resume_id", RESUME_IDS)
    def test_inject_passive_voice_lowers_writing_score(self, resume_id, resumes, matcher):
        base = WritingScorer().score(resumes[resume_id], None, matcher)
        degraded = WritingScorer().score(inject_passive_voice(resumes[resume_id]), None, matcher)
        assert base.status == "scored" and degraded.status == "scored"
        assert degraded.score < base.score, f"{resume_id}: {degraded.score} !< {base.score}"


class TestRepetitionLowersWriting:
    @pytest.mark.parametrize("resume_id", RESUME_IDS)
    def test_inject_repetition_lowers_writing_score(self, resume_id, resumes, matcher):
        base = WritingScorer().score(resumes[resume_id], None, matcher)
        degraded = WritingScorer().score(inject_repetition(resumes[resume_id]), None, matcher)
        assert base.status == "scored" and degraded.status == "scored"
        assert degraded.score < base.score, f"{resume_id}: {degraded.score} !< {base.score}"


class TestFillerLowersWriting:
    @pytest.mark.parametrize("resume_id", RESUME_IDS)
    def test_add_filler_lowers_writing_score(self, resume_id, resumes, matcher):
        base = WritingScorer().score(resumes[resume_id], None, matcher)
        degraded = WritingScorer().score(add_filler(resumes[resume_id]), None, matcher)
        assert base.status == "scored" and degraded.status == "scored"
        assert degraded.score < base.score, f"{resume_id}: {degraded.score} !< {base.score}"
