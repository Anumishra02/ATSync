"""The six scoring dimensions, each wrapping existing (tested) logic.

Per the evaluation cycle's backlog (evaluation/backlog.md), this
increment deliberately does NOT change the underlying logic of Structure,
Writing, or Achievements -- they're wrapped as-is. Two dimensions ARE
built differently than the live route currently computes them, because
the backlog specifically identified why the old computation carries no
signal:

  Relevance   Uses score_resume (weighted by JD emphasis, evidence-linked)
              instead of legacy_ats_score's keyword_score. The backlog's
              regression found keyword_score's plain word-overlap
              uncorrelated with human relevance judgment (r^2=0.018,
              p=0.71) -- "no concept of what a human means by relevant."
              score_resume already exists and is tested; it just wasn't
              wired into anything live yet.
  Experience  New. No prior implementation to preserve -- the backlog's
              single largest gap (20/100 rubric points, unmeasured on
              every one of the 39 evaluated resumes). Calibrated against
              that same 39-resume corpus (see the module-level constants).

Skills keeps legacy_ats_score's skill_score-style computation (flat
match-rate, not emphasis-weighted) specifically so it stays a different
signal from Relevance rather than a duplicate of it under another name --
Skills answers "did the resume name the right skills," Relevance answers
"how strongly does the resume align with what this JD actually
emphasizes."

Max points (relevance 15, skills 15, experience 20, achievements 20,
writing 15, structure 15 -- summing to 100) match Resume-Scores-39.xlsx's
"Rubric & Notes" sheet exactly, not the illustrative numbers from the
Phase 0 discussion, so machine dimension scores stay comparable to the 39
human labels already collected.
"""

from __future__ import annotations

from typing import Protocol

from services.analyzer import check_quantification, check_repetition
from services.matching.chunking import ChunkKind, chunk_job_description, chunk_resume
from services.scoring import check_sections, score_resume
from services.skills.matcher import SkillMatcher

from .models import DimensionResult


class Scorer(Protocol):
    name: str
    max_points: float
    requires_jd: bool

    def score(self, resume_text: str, jd_text: str | None, matcher: SkillMatcher) -> DimensionResult: ...


class StructureScorer:
    """Section-heading presence -- see services/scoring.py's check_sections."""

    name = "structure"
    max_points = 15.0
    requires_jd = False

    def score(self, resume_text: str, jd_text: str | None, matcher: SkillMatcher) -> DimensionResult:
        chunks = chunk_resume(resume_text)
        sections = check_sections(chunks)
        found, total = sum(sections.values()), len(sections)
        pct = found / total if total else 0.0
        return DimensionResult(
            dimension=self.name,
            score=round(pct * self.max_points, 1),
            max_points=self.max_points,
            status="scored",
            detail={"sections": sections},
        )


class WritingScorer:
    """Word-repetition proxy -- see analyzer.check_repetition.

    Deliberately NOT folding in check_grammar (Gemini-dependent) in this
    pass -- see the module docstring on why this dimension is wrapped
    as-is rather than fixed. check_repetition's own known bug (flags
    legitimate technical-term repetition, e.g. "Python" appearing 4+ times
    in a technical resume, as if it were poor word choice -- see
    backlog.md item 4) is inherited here on purpose, not fixed in this
    pass.
    """

    name = "writing"
    max_points = 15.0
    requires_jd = False

    def score(self, resume_text: str, jd_text: str | None, matcher: SkillMatcher) -> DimensionResult:
        result = check_repetition(resume_text)
        pct = result["score"] / 100.0
        return DimensionResult(
            dimension=self.name,
            score=round(pct * self.max_points, 1),
            max_points=self.max_points,
            status="scored",
            detail={"repeated_words": result["repeated_words"]},
        )


class AchievementsScorer:
    """Quantified-bullet rate -- see analyzer.check_quantification.

    Already returns score=None (uncomputable) for a resume with no real
    bulleted content -- that maps directly onto this model's status field.
    """

    name = "achievements"
    max_points = 20.0
    requires_jd = False

    def score(self, resume_text: str, jd_text: str | None, matcher: SkillMatcher) -> DimensionResult:
        result = check_quantification(resume_text)
        if result["score"] is None:
            return DimensionResult(
                dimension=self.name, score=None, max_points=self.max_points, status="uncomputable",
                detail={"reason": result["verdict"]},
            )
        pct = result["score"] / 100.0
        return DimensionResult(
            dimension=self.name,
            score=round(pct * self.max_points, 1),
            max_points=self.max_points,
            status="scored",
            detail={"total_bullets": result["total_bullets"], "quantified": result["quantified"]},
        )


# Calibrated against the 39-resume evaluation corpus (evaluation/): recognized
# -skill counts for genuinely strong software/data/ML résumés in that corpus
# (the only fields skills_seed.json's 92-skill taxonomy has real vocabulary
# for) clustered 11-31; 12 sits at the low end of that cluster, so a resume
# needs to be genuinely skill-rich, not just skill-present, to max out.
#
# KNOWN, DOCUMENTED LIMITATION, not silently absorbed: for the ~30 non-tech
# fields in that same corpus (art history, accounting, marketing, ...) this
# scorer reads as near-zero regardless of actual skill quality, because the
# taxonomy has almost no vocabulary for those domains -- the same
# taxonomy-coverage gap the backlog documents on the JD-relevance side (see
# resume_eval_predict.py's taxonomy_covered flag). Growing the taxonomy
# fixes both at once; this scorer isn't a separate bug to chase.
_SKILLS_NO_JD_TARGET_COUNT = 12


class SkillsScorer:
    """Skill-name match rate.

    Dual mode, per the Phase 0 spec: with a JD, "how well do the
    candidate's skills match this job" (flat match-rate against the JD's
    own required skills). Without one, "how many recognized skills does
    this résumé contain at all" (see _SKILLS_NO_JD_TARGET_COUNT for the
    calibration and its documented taxonomy-coverage caveat).
    """

    name = "skills"
    max_points = 15.0
    requires_jd = False  # can run without a JD -- see the table in the Phase 0 spec

    def score(self, resume_text: str, jd_text: str | None, matcher: SkillMatcher) -> DimensionResult:
        resume_skill_ids = matcher.extract(resume_text).skill_ids

        if jd_text is None:
            pct = min(len(resume_skill_ids) / _SKILLS_NO_JD_TARGET_COUNT, 1.0)
            return DimensionResult(
                dimension=self.name,
                score=round(pct * self.max_points, 1),
                max_points=self.max_points,
                status="scored",
                detail={"mode": "count", "skills_found": len(resume_skill_ids)},
            )

        jd_skill_ids = matcher.extract(jd_text).skill_ids
        if not jd_skill_ids:
            # The JD itself named no recognized skills -- not the résumé's
            # fault, and not the same failure as "no résumé content to
            # read" (Achievements' uncomputable case), but equally not a
            # rate you can compute a numerator/denominator for.
            return DimensionResult(
                dimension=self.name, score=None, max_points=self.max_points, status="uncomputable",
                detail={"reason": "JD named no recognized taxonomy skills"},
            )
        matched = jd_skill_ids & resume_skill_ids
        pct = len(matched) / len(jd_skill_ids)
        return DimensionResult(
            dimension=self.name,
            score=round(pct * self.max_points, 1),
            max_points=self.max_points,
            status="scored",
            detail={"mode": "jd_match", "matched": len(matched), "jd_skills": len(jd_skill_ids)},
        )


class RelevanceScorer:
    """JD-alignment, weighted by requirement emphasis (required > preferred).

    Uses score_resume, not legacy_ats_score's keyword_score -- see the
    module docstring for why (backlog.md's regression finding). Always
    requires a JD; that's the dimension's entire reason to exist.
    """

    name = "relevance"
    max_points = 15.0
    requires_jd = True

    def score(self, resume_text: str, jd_text: str | None, matcher: SkillMatcher) -> DimensionResult:
        if jd_text is None:
            return DimensionResult(
                dimension=self.name, score=None, max_points=self.max_points, status="not_applicable",
            )
        result = score_resume(matcher, resume_text, jd_text)
        pct = result.score / 100.0
        return DimensionResult(
            dimension=self.name,
            score=round(pct * self.max_points, 1),
            max_points=self.max_points,
            status="scored",
            detail={"matched": len(result.matched), "missing": len(result.missing)},
        )


# Calibrated against the 39-resume evaluation corpus, using "experience" as
# a case-insensitive SUBSTRING of the chunker's raw section label, not an
# exact match -- real résumés use "Work Experience", "Leadership
# Experience", "Marketing Experience", "Accounting Experience", none of
# which equal the literal string "experience". An exact-match version of
# this scorer found zero experience content on 33 of the 39 resumes; the
# substring version found content on 38/39 (the one miss, R28, is a real
# PDF font-encoding failure upstream in extraction, not a scorer bug --
# its section headings extract as "ane oe" / "j d").
#
# Bullets, not prose lines, are the primary signal: résumés the human rater
# scored >=16/20 clustered at 7-17 experience bullets; most résumés scored
# <=9/20 had ZERO experience bullets (prose-only role descriptions --
# "Company, Title, Dates" with no elaboration of what was actually done).
# 10 sits near the median of the strong cluster. Prose-line count (a rough
# proxy for how many distinct roles are described) contributes a smaller
# secondary weight.
_EXPERIENCE_TARGET_BULLETS = 10
_EXPERIENCE_TARGET_ENTRIES = 3
_EXPERIENCE_BULLET_WEIGHT = 0.75


class ExperienceScorer:
    """Depth of the experience section: bullet count (primary) and
    distinct-entry count (secondary), both scoped to sections whose raw
    heading contains "experience".

    New dimension -- no prior implementation existed. See backlog.md:
    "the only backlog item that's a missing capability rather than a bug."
    This is a first, real, calibrated pass, not a claim of completeness --
    it does not yet look at role ordering, date gaps, or seniority
    (deferred; see the framing-gap discussion's Phase C).
    """

    name = "experience"
    max_points = 20.0
    requires_jd = False

    def score(self, resume_text: str, jd_text: str | None, matcher: SkillMatcher) -> DimensionResult:
        chunks = chunk_resume(resume_text)
        exp_bullets = [
            c for c in chunks
            if c.kind is ChunkKind.BULLET and c.section and "experience" in c.section
        ]
        exp_entries = [
            c for c in chunks
            if c.kind is ChunkKind.PROSE and c.section and "experience" in c.section and c.is_scorable
        ]
        if not exp_bullets and not exp_entries:
            return DimensionResult(
                dimension=self.name, score=None, max_points=self.max_points, status="uncomputable",
                detail={"reason": "no section containing 'experience' found with any content"},
            )

        bullet_component = min(len(exp_bullets) / _EXPERIENCE_TARGET_BULLETS, 1.0)
        entry_component = min(len(exp_entries) / _EXPERIENCE_TARGET_ENTRIES, 1.0)
        pct = _EXPERIENCE_BULLET_WEIGHT * bullet_component + (1 - _EXPERIENCE_BULLET_WEIGHT) * entry_component
        return DimensionResult(
            dimension=self.name,
            score=round(pct * self.max_points, 1),
            max_points=self.max_points,
            status="scored",
            detail={"bullets": len(exp_bullets), "entries": len(exp_entries)},
        )


ALL_SCORERS: tuple[Scorer, ...] = (
    StructureScorer(),
    WritingScorer(),
    AchievementsScorer(),
    SkillsScorer(),
    ExperienceScorer(),
    RelevanceScorer(),
)
