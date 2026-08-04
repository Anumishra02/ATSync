"""One test that crosses the whole system: PDF bytes in, a score out.

131 unit tests existed before this file and none of them exercised more
than one layer at a time. Several real bugs this session (the 3-word
scorable floor dropping every terse skills bullet, Title Case headings
misclassifying job titles, check_sections regex-matching the whole body)
were found by wiring layers together, not by any individual layer's own
tests passing. This test is the standing version of that check: it would
have failed on all three, and stays here so the next integration bug gets
caught the same way instead of shipped.

Deliberately uses the *two-column* Canva-style fixture as the resume, not
the easy single-column one -- if reading-order reconstruction regresses,
this is where it would show up as a wrong score, not just a wrong text
diff in test_pdf_extract.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from services.matching.chunking import normalize_document_text
from services.parsing.pdf_extract import extract_text_from_pdf
from services.scoring import check_sections, legacy_ats_score, score_resume
from services.matching.chunking import chunk_resume
from services.skills.matcher import SkillMatcher
from services.skills.taxonomy import Taxonomy

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "pdfs"
SEED = Path(__file__).resolve().parents[1] / "data" / "skills_seed.json"

JD = """\
Requirements

• Strong Python programming experience required
• Must have hands-on experience with Docker in production
• Experience building backend services with FastAPI

Nice to Have

• Familiarity with Kubernetes
"""


@pytest.fixture(scope="module")
def matcher() -> SkillMatcher:
    return SkillMatcher(Taxonomy.from_seed_json(SEED))


@pytest.fixture(scope="module")
def resume_text() -> str:
    """The full pipeline's first hop: real PDF bytes -> extracted text.

    Canva-style is two-column -- this is the fixture that actually
    exercises reading-order reconstruction, not just text extraction.
    """
    pdf_bytes = (FIXTURES / "canva_style.pdf").read_bytes()
    raw = extract_text_from_pdf(pdf_bytes)
    return normalize_document_text(raw)


class TestPdfToScore:
    def test_extraction_survives_the_two_column_layout(self, resume_text):
        # If reading order broke, "FastAPI" and "PostgreSQL" would not
        # appear near each other in one coherent bullet -- this is a loose
        # smoke check; test_pdf_extract.py's exact word-order assertion is
        # the precise one. This test's job is to fail loudly if extraction
        # produces empty or garbage text before scoring even runs.
        assert "Python" in resume_text
        assert "FastAPI" in resume_text
        assert "Docker" in resume_text
        assert len(resume_text.split()) > 100

    def test_score_resume_end_to_end(self, matcher, resume_text):
        result = score_resume(matcher, resume_text, normalize_document_text(JD))

        matched_ids = {m.skill_id for m in result.matched}
        missing_ids = {m.skill_id for m in result.missing}

        assert {"python", "docker", "fastapi"} <= matched_ids
        assert "kubernetes" in missing_ids

        # The score is recomputable by hand from the response, same
        # invariant test_scoring.py holds the underlying formula to --
        # this just proves it still holds once a real PDF is the input.
        assert result.score == round(100 * result.weight_matched / result.weight_total)
        # 3 required skills matched (weight 1.0 each) + 1 preferred missing
        # (weight 0.4): 3.0 / 3.4 ~= 88%.
        assert result.score == 88

    def test_evidence_offsets_are_valid_against_the_extracted_text(self, matcher, resume_text):
        # Evidence offsets are chunk-relative-to-resume_text, per
        # score_resume's contract -- prove they still resolve correctly
        # once resume_text came from a real PDF instead of a hand-written
        # fixture string.
        result = score_resume(matcher, resume_text, normalize_document_text(JD))
        for m in result.matched:
            span = resume_text[m.evidence.char_start : m.evidence.char_end]
            assert span, f"{m.name}: empty span at offsets {m.evidence.char_start}:{m.evidence.char_end}"

    def test_sections_are_detected_from_the_real_pdf(self, resume_text):
        chunks = chunk_resume(resume_text)
        sections = check_sections(chunks)
        assert sections["experience"] is True
        assert sections["education"] is True
        assert sections["skills"] is True
        assert sections["projects"] is True
        assert sections["certifications"] is True

    def test_legacy_endpoint_shape_end_to_end(self, matcher, resume_text):
        # routes/resume.py's actual call path (legacy_ats_score, not
        # score_resume directly) -- same PDF, same JD, the shape the live
        # /score and /analyze endpoints actually return.
        result = legacy_ats_score(matcher, resume_text, normalize_document_text(JD))
        assert "Python" in result["matched_skills"]
        assert "Docker" in result["matched_skills"]
        assert "Kubernetes" in result["missing_skills"]
        assert result["ats_score"] > 0

    def test_single_column_and_two_column_fixtures_score_identically(self, matcher):
        # The whole point of column detection: the same underlying resume
        # content should score the same regardless of which layout it was
        # exported in. word_style.pdf (single column) and canva_style.pdf
        # (two column) are the same Priya Sharma content -- if reading
        # order breaks on one, this catches it as a score divergence, not
        # just a text-order difference.
        jd = normalize_document_text(JD)
        single = normalize_document_text(extract_text_from_pdf((FIXTURES / "word_style.pdf").read_bytes()))
        two_col = normalize_document_text(extract_text_from_pdf((FIXTURES / "canva_style.pdf").read_bytes()))

        score_single = score_resume(matcher, single, jd).score
        score_two_col = score_resume(matcher, two_col, jd).score
        assert score_single == score_two_col
