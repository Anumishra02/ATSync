"""Run all six scorers, respecting each one's requires_jd flag, and
determine the analysis mode.

    jd_text is None   -> mode="quality" (Structure/Writing/Achievements/
                          Skills/Experience run; Relevance does not)
    jd_text given      -> mode="match" (all six run)

A scorer whose requires_jd is True is never even called when there's no
JD -- not called-and-discarded, not called-with-jd=None-and-trusted-to-
do-the-right-thing. The pipeline decides that up front and constructs the
not_applicable result itself, so "does this dimension run" is answered in
exactly one place.
"""

from __future__ import annotations

from services.skills.matcher import SkillMatcher

from .models import AnalysisResult, DimensionResult
from .scorers import ALL_SCORERS, Scorer


def run_analysis(
    resume_text: str,
    jd_text: str | None,
    matcher: SkillMatcher,
    scorers: tuple[Scorer, ...] = ALL_SCORERS,
) -> AnalysisResult:
    mode = "quality" if jd_text is None else "match"
    dimensions: list[DimensionResult] = []

    for scorer in scorers:
        if scorer.requires_jd and jd_text is None:
            dimensions.append(DimensionResult(
                dimension=scorer.name, score=None, max_points=scorer.max_points,
                status="not_applicable",
            ))
            continue
        dimensions.append(scorer.score(resume_text, jd_text, matcher))

    return AnalysisResult(mode=mode, dimensions=dimensions)
