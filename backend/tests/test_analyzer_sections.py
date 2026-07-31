"""Regression test for analyzer.check_sections's heading-detection fix.

Only check_sections is exercised here -- the rest of analyzer.py (grammar
check) calls the Gemini API and has no place in the fast, offline suite.
"""

from __future__ import annotations

from services.analyzer import check_sections


def test_body_words_no_longer_fake_a_section():
    """The original v1 bug: 'developed' anywhere meant a Projects section
    existed, and 'work' meant an Experience section did. Nearly every
    resume scored full marks on a check that measured nothing.
    """
    text = "SUMMARY\n\nI developed several systems and did great work.\n"
    s = check_sections(text)
    assert s["sections"]["Projects"] is False
    assert s["sections"]["Experience"] is False
    assert s["found"] == 0


def test_real_headings_are_detected():
    resume = (
        "EXPERIENCE\n\nBackend Engineer\nBuilt things.\n\n"
        "EDUCATION\n\nB.Tech\n\n"
        "SKILLS\n\nPython, Docker\n"
    )
    s = check_sections(resume)
    assert s["sections"]["Experience"] is True
    assert s["sections"]["Education"] is True
    assert s["sections"]["Skills"] is True
    assert s["sections"]["Projects"] is False
    assert s["found"] == 3


def test_return_shape_is_unchanged():
    s = check_sections("EXPERIENCE\n\nBuilt things.\n")
    assert set(s) == {"score", "sections", "found", "total", "issues", "verdict", "tip"}
    assert set(s["sections"]) == {
        "Education", "Experience", "Skills", "Projects", "Certifications",
    }
