"""Tests for check_quantification's chunker-sourced bullets and
full_analysis's handling of an uncomputable sub-score.

Only these two are exercised here -- the rest of analyzer.py's full_analysis
pulls in check_grammar (Gemini API), which has no place in the fast,
offline suite (see test_analyzer_sections.py).
"""

from __future__ import annotations

from services.analyzer import check_quantification, full_analysis


def test_mid_word_hyphens_no_longer_fabricate_or_truncate_bullets():
    # The old regex (`[•\-\*]\s*(.+)`) treated any hyphen as a bullet
    # marker. "Full-stack" in a Summary line and "Front-End" in a job-title
    # line used to each spawn a phantom bullet with no number, dragging the
    # score down for content that was never a bullet at all.
    text = (
        "Summary\n"
        "Full-stack web developer who ships fast.\n\n"
        "Experience\n"
        "Software Engineer (Front-End)\n"
        "- Cut page load time by 45% through code-splitting and lazy loading\n"
        "- Built a back-end REST service in Java\n"
    )
    result = check_quantification(text)
    # Real bullets: the 45% one (quantified) and the back-end one (not).
    # No phantom fragments from "Full-stack" / "Front-End" / "code-splitting".
    assert result["total_bullets"] == 2
    assert result["quantified"] == 1
    assert result["score"] == 50


def test_skills_section_bullets_are_excluded():
    text = (
        "Skills\n"
        "- Python\n"
        "- Docker\n"
        "- Kubernetes\n\n"
        "Experience\n"
        "- Shipped a feature to 2M+ users\n"
    )
    result = check_quantification(text)
    assert result["total_bullets"] == 1
    assert result["quantified"] == 1


def test_no_bullets_is_uncomputable_not_zero():
    # A pure-prose resume (no glyph bullets anywhere) has nothing this check
    # can read. It should say so, not report a confident 0%.
    text = (
        "Experience\n"
        "Developed and implemented a streamlined process for gathering "
        "requirements, reducing delivery time by 15%.\n"
    )
    result = check_quantification(text)
    assert result["score"] is None
    assert result["total_bullets"] == 0
    assert result["issues"] == 0


def test_full_analysis_redistributes_weight_around_uncomputable_quantification():
    # overall_score should stay on the 0-100 scale (not silently capped
    # below 100, not punished as if quantification scored 0) when
    # quantification can't be assessed.
    prose_resume = (
        "Experience\n"
        "Developed and implemented a streamlined process for gathering "
        "requirements, reducing delivery time by 15%.\n"
    )
    ats = {"ats_score": 80}
    result = full_analysis(prose_resume, "resume.pdf", 100_000, "some jd text", ats)
    assert result["categories"]["quantification"]["score"] is None
    # 6 of 7 weighted components ran; overall_score is still a plain 0-100
    # number, not None and not silently deflated by the missing 15% weight.
    assert isinstance(result["overall_score"], int)
    assert 0 <= result["overall_score"] <= 100
