"""ATS scoring: the service the API calls.

Replaces v1's ``ats_scorer.calculate_ats_score`` and ``analyzer.check_sections``.

Three things it does that v1 could not:

1. **Weights by emphasis.** A skill named in a "must have" line counts more
   than one under "nice to have". v1 weighted every keyword identically,
   which is also what every commercial scanner does.
2. **Returns evidence, not just verdicts.** Each matched skill carries the
   resume chunk it was found in plus char offsets, so the UI can highlight
   the proof. Each miss carries the requirement that wanted it, so the user
   is told *why* something is missing.
3. **Reads real section headings.** v1 regex-matched the body text, so the
   word "developed" anywhere meant "has a Projects section" -- nearly every
   resume scored full marks on a check that measured nothing.

The score itself is deliberately simple and inspectable: weighted coverage
of the skills a JD asks for. No LLM in the path. It is a number you can
recompute by hand from the response, which matters when a user asks why
they got a 62.

``score_resume``/``ScoreResult`` are this module's real API -- richer than
what the live routes currently expose (evidence links, per-skill weight).
Wiring that into the frontend is separate work (the response shape isn't
what the UI renders today). ``legacy_ats_score`` below is the drop-in used
by the existing endpoints right now: same skill-matching engine, same
heading-based section detection, but shaped exactly like v1's
``calculate_ats_score`` so nothing downstream (routes, ``analyzer.py``, the
frontend) needs to change to get the bug fixes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from services.matching.chunking import (
    Chunk,
    ChunkKind,
    Emphasis,
    chunk_job_description,
    chunk_resume,
)
from services.skills.matcher import SkillMatcher

# A required skill counts for full weight; a preferred one is worth less but
# not nothing. Unspecified sits between: the JD asked for it without saying
# how badly.
EMPHASIS_WEIGHT: dict[Emphasis, float] = {
    Emphasis.REQUIRED: 1.0,
    Emphasis.UNSPECIFIED: 0.7,
    Emphasis.PREFERRED: 0.4,
    Emphasis.BOILERPLATE: 0.0,
}

# Sections a reviewer expects. Absence is a real signal; v1's version was not.
EXPECTED_SECTIONS: dict[str, tuple[str, ...]] = {
    "experience": ("experience", "employment", "work history", "professional experience"),
    "education": ("education", "academics", "qualifications"),
    "skills": ("skills", "technical skills", "core competencies", "technologies"),
    "projects": ("projects", "personal projects", "academic projects"),
    "certifications": ("certifications", "awards", "achievements", "publications"),
}


@dataclass(frozen=True, slots=True)
class Evidence:
    """Where in the resume a skill was found."""

    text: str
    section: str | None
    char_start: int
    char_end: int
    tier: str


@dataclass(frozen=True, slots=True)
class MatchedSkill:
    skill_id: str
    name: str
    weight: float
    evidence: Evidence


@dataclass(frozen=True, slots=True)
class MissingSkill:
    skill_id: str
    name: str
    weight: float
    emphasis: str
    requirement: str


@dataclass
class ScoreResult:
    # None means uncomputable, not a confident zero -- see score_resume's
    # docstring. A resume-independent 0 (every JD requirement unweighted,
    # weight_total == 0) means the JD gave nothing to compare against, not
    # that the resume failed to match anything.
    score: int | None
    matched: list[MatchedSkill] = field(default_factory=list)
    missing: list[MissingSkill] = field(default_factory=list)
    sections: dict[str, bool] = field(default_factory=dict)
    weight_matched: float = 0.0
    weight_total: float = 0.0

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "matched": [asdict(m) for m in self.matched],
            "missing": [asdict(m) for m in self.missing],
            "sections": self.sections,
            "coverage": {
                "matched": round(self.weight_matched, 3),
                "total": round(self.weight_total, 3),
            },
        }


def check_sections(chunks: list[Chunk]) -> dict[str, bool]:
    """Section presence from actual headings.

    v1 searched the whole body for words like "developed" and "work", so
    almost every resume passed every check. This looks only at lines the
    chunker classified as headings.
    """
    headings = {c.text.strip().rstrip(":").lower() for c in chunks if c.kind is ChunkKind.HEADING}
    found: dict[str, bool] = {}
    for name, aliases in EXPECTED_SECTIONS.items():
        found[name] = any(
            alias == h or alias in h for h in headings for alias in aliases
        )
    return found


def _requirement_weights(
    matcher: SkillMatcher, jd_chunks: list[Chunk]
) -> tuple[dict[str, float], dict[str, tuple[str, Emphasis]]]:
    """Per-skill weight, and the strongest requirement that asked for it."""
    weights: dict[str, float] = {}
    origin: dict[str, tuple[str, Emphasis]] = {}

    for chunk in jd_chunks:
        if not chunk.is_scorable:
            continue
        w = EMPHASIS_WEIGHT.get(chunk.emphasis, 0.7)
        if w == 0.0:
            continue
        for skill_id, match in matcher.extract(chunk.text).best_per_skill().items():
            # A skill named under both "required" and "nice to have" takes the
            # higher weight -- the JD asked for it at least that strongly.
            if w > weights.get(skill_id, 0.0):
                weights[skill_id] = w
                origin[skill_id] = (chunk.text, chunk.emphasis)
            weights.setdefault(skill_id, w)
            origin.setdefault(skill_id, (chunk.text, chunk.emphasis))
            del match
    return weights, origin


def score_resume(
    matcher: SkillMatcher, resume_text: str, jd_text: str
) -> ScoreResult:
    """Score a resume against a job description.

    Both texts must already be normalized (see chunking's precondition).

    Returns score=None (uncomputable, not a confident 0) when the JD
    yields zero weighted requirements at all (weight_total == 0) --
    e.g. an empty JD, or one whose extractor (seed, or the ESCO fallback
    via HybridSkillMatcher when both layers come up empty) finds nothing
    to grade against. The guard is written against `total`, the extractor
    chain's actual output, not against which matcher produced it -- this
    behaves identically whether `matcher` is a plain SkillMatcher or a
    HybridSkillMatcher, by construction, not by a special case for either.
    A JD with genuinely no recognizable requirement is a case with nothing
    to compare the resume against, not a case where the resume failed to
    match anything -- those are different claims, and returning 0 for both
    conflated them. Found while re-running the relevance contrast test
    (Phase C1): the same failure class check_quantification's uncomputable
    guard was built for, in a different scoring path.
    """
    resume_chunks = chunk_resume(resume_text)
    jd_chunks = chunk_job_description(jd_text)

    weights, origin = _requirement_weights(matcher, jd_chunks)
    sections = check_sections(resume_chunks)

    # Best evidence per skill across the whole resume.
    evidence: dict[str, Evidence] = {}
    names: dict[str, str] = {}
    for chunk in resume_chunks:
        if not chunk.is_scorable:
            continue
        for skill_id, match in matcher.extract(chunk.text).best_per_skill().items():
            names[skill_id] = match.skill.canonical
            if skill_id in evidence:
                continue
            evidence[skill_id] = Evidence(
                text=chunk.text,
                section=chunk.section,
                char_start=chunk.char_start + match.char_start,
                char_end=chunk.char_start + match.char_end,
                tier=match.tier.value,
            )

    matched: list[MatchedSkill] = []
    missing: list[MissingSkill] = []
    for skill_id, weight in weights.items():
        canonical = names.get(skill_id) or matcher.taxonomy.get(skill_id)
        name = canonical if isinstance(canonical, str) else (
            canonical.canonical if canonical else skill_id
        )
        if skill_id in evidence:
            matched.append(MatchedSkill(skill_id, name, weight, evidence[skill_id]))
        else:
            req, emph = origin[skill_id]
            missing.append(MissingSkill(skill_id, name, weight, emph.value, req))

    total = sum(weights.values())
    got = sum(m.weight for m in matched)
    score = round(100 * got / total) if total else None

    matched.sort(key=lambda m: (-m.weight, m.name))
    missing.sort(key=lambda m: (-m.weight, m.name))

    return ScoreResult(
        score=score,
        matched=matched,
        missing=missing,
        sections=sections,
        weight_matched=got,
        weight_total=total,
    )


def legacy_ats_score(matcher: SkillMatcher, resume_text: str, jd_text: str) -> dict:
    """Drop-in replacement for ``ats_scorer.calculate_ats_score``.

    Same return shape and same 70/30 skill/keyword formula as v1 -- so
    ``routes/resume.py`` and ``analyzer.full_analysis`` don't need to change
    -- but skill extraction and matching go through ``SkillMatcher`` instead
    of v1's substring check. That's the actual live bug this fixes: v1
    matched "java" inside "javascript", "git" inside "github", "sql" inside
    "postgresql" (see services/skills/README.md), both when pulling skills
    out of the JD and, separately, when checking whether the resume
    contained them (v1 re-did the same substring check against the resume
    text, which had the identical bug on the other side).

    ``score_resume``/``ScoreResult`` above is the richer replacement for
    when the frontend is ready for evidence links and emphasis weighting;
    this function exists so the fix ships without waiting for that.

    Both texts must already be normalized (same precondition as
    ``score_resume`` and chunking -- normalize once at the API boundary,
    not redundantly in every function that touches the text).
    """
    import re

    resume_result = matcher.extract(resume_text).best_per_skill()
    jd_result = matcher.extract(jd_text).best_per_skill()

    jd_skill_ids = list(jd_result.keys())
    matched_skills = [jd_result[sid].skill.canonical for sid in jd_skill_ids if sid in resume_result]
    missing_skills = [jd_result[sid].skill.canonical for sid in jd_skill_ids if sid not in resume_result]

    jd_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", jd_text.lower()))
    resume_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", resume_text.lower()))
    keyword_overlap = jd_words & resume_words
    keyword_score = min(len(keyword_overlap) / max(len(jd_words), 1) * 100, 100)

    skill_score = (len(matched_skills) / len(jd_skill_ids) * 100) if jd_skill_ids else 0
    final_score = round((skill_score * 0.7) + (keyword_score * 0.3), 2)

    if final_score >= 80:
        grade, verdict = "Excellent", "Strong match! Your resume aligns well with this job."
    elif final_score >= 60:
        grade, verdict = "Good", "Decent match. Add missing skills to improve your chances."
    elif final_score >= 40:
        grade, verdict = "Average", "Partial match. Significant skill gaps need to be addressed."
    else:
        grade, verdict = "Poor", "Weak match. Resume needs major improvements for this role."

    return {
        "ats_score": final_score,
        "grade": grade,
        "verdict": verdict,
        "skill_score": round(skill_score, 2),
        "keyword_score": round(keyword_score, 2),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "total_jd_skills": len(jd_skill_ids),
        "total_matched": len(matched_skills),
        "summary": (
            f"Your resume matched {len(matched_skills)} out of {len(jd_skill_ids)} required skills. "
            f"Missing: {', '.join(missing_skills) if missing_skills else 'nothing!'}"
        ),
    }
