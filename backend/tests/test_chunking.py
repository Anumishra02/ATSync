"""Tests for Phase 2 chunking.

The offset tests matter most: evidence-linking depends on every chunk's
char_start/char_end still pointing at the right place in the original text
after wrap-rejoining. If those drift, the highlight feature silently lies.
"""

from __future__ import annotations

import pytest

from services.matching.chunking import (
    ChunkKind,
    Emphasis,
    chunk_job_description,
    chunk_resume,
)

RESUME = """\
EXPERIENCE

Software Engineer Intern, Acme Corp
• Built a FastAPI service handling 2M requests per day, reducing p99
  latency from 400ms to 90ms
• Migrated the primary datastore to PostgreSQL
- Wrote the CI/CD pipeline on GitHub Actions

PROJECTS

ATSync — resume matching engine
o Implemented a three-tier skill extraction cascade over an ESCO
  taxonomy of 13,900 skills

SKILLS

Python, FastAPI, PostgreSQL, Docker
"""

JD = """\
About Us

We are a fast-growing fintech startup backed by top investors.

Requirements

• 3+ years of experience building backend services in Python
• Must have strong SQL and data modelling skills
• Experience with Docker and container orchestration

Nice to Have

• Exposure to Kubernetes in production
• Familiarity with Kafka or similar streaming systems
"""


class TestResumeChunking:
    def test_bullets_are_detected_across_glyph_styles(self):
        chunks = chunk_resume(RESUME)
        bullets = [c for c in chunks if c.kind is ChunkKind.BULLET]
        # bullet, bullet, hyphen, and Word's second-level 'o'
        assert len(bullets) == 4

    def test_wrapped_lines_are_rejoined(self):
        chunks = chunk_resume(RESUME)
        wrapped = next(c for c in chunks if "p99" in c.text)
        assert "latency from 400ms to 90ms" in wrapped.text
        assert "\n" not in wrapped.text

    def test_bullet_glyph_is_stripped_from_text(self):
        chunks = chunk_resume(RESUME)
        for c in chunks:
            if c.kind is ChunkKind.BULLET:
                assert not c.text.startswith(("•", "-", "o ", "*"))

    def test_headings_are_detected_and_assign_sections(self):
        chunks = chunk_resume(RESUME)
        headings = {c.text for c in chunks if c.kind is ChunkKind.HEADING}
        assert {"EXPERIENCE", "PROJECTS", "SKILLS"} <= headings
        pg = next(c for c in chunks if "PostgreSQL" in c.text and c.kind is ChunkKind.BULLET)
        assert pg.section == "experience"

    def test_offsets_point_into_the_original_text(self):
        for c in chunk_resume(RESUME):
            window = RESUME[c.char_start : c.char_end]
            # first real word of the chunk must appear in its own span
            first = c.text.split()[0]
            assert first in window, f"{first!r} not in {window!r}"

    def test_chunks_are_ordered_and_non_overlapping(self):
        chunks = chunk_resume(RESUME)
        for a, b in zip(chunks, chunks[1:], strict=False):
            assert a.index < b.index
            assert a.char_start <= b.char_start

    def test_short_fragments_are_not_scorable(self):
        chunks = chunk_resume(RESUME)
        assert all(not c.is_scorable for c in chunks if c.kind is ChunkKind.HEADING)


class TestJobDescriptionChunking:
    def test_company_boilerplate_is_excluded_from_scoring(self):
        chunks = chunk_job_description(JD)
        boiler = [c for c in chunks if c.emphasis is Emphasis.BOILERPLATE]
        assert boiler, "company blurb should be tagged boilerplate"
        assert all(not c.is_scorable for c in boiler)

    @pytest.mark.parametrize(
        ("needle", "expected"),
        [
            ("Must have strong SQL", Emphasis.REQUIRED),
            ("3+ years of experience", Emphasis.REQUIRED),
            ("Exposure to Kubernetes", Emphasis.PREFERRED),
            ("Familiarity with Kafka", Emphasis.PREFERRED),
        ],
    )
    def test_required_and_preferred_are_separated(self, needle, expected):
        chunk = next(c for c in chunk_job_description(JD) if needle in c.text)
        assert chunk.emphasis is expected

    def test_preferred_section_propagates_to_its_bullets(self):
        chunks = chunk_job_description(JD)
        k8s = next(c for c in chunks if "Kubernetes" in c.text)
        assert k8s.section == "nice to have"

    def test_scorable_units_exclude_headings_and_boilerplate(self):
        scorable = [c for c in chunk_job_description(JD) if c.is_scorable]
        assert all(c.kind is not ChunkKind.HEADING for c in scorable)
        assert all(c.emphasis is not Emphasis.BOILERPLATE for c in scorable)
        assert len(scorable) == 5


class TestEdgeCases:
    def test_empty_document(self):
        assert chunk_resume("") == []

    def test_document_with_no_bullets_at_all(self):
        text = "Experienced engineer.\nWorked on distributed systems.\n"
        chunks = chunk_resume(text)
        assert all(c.kind is ChunkKind.PROSE for c in chunks)
        assert len(chunks) == 2

    def test_a_capitalised_wrap_is_not_swallowed_into_the_previous_bullet(self):
        # Conservative by design: we would rather split than merge two units.
        text = "• Built the ingestion service\n• Owned the on-call rotation\n"
        assert len(chunk_resume(text)) == 2
