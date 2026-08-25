"""Tests for Phase 2 chunking.

The offset tests matter most: evidence-linking depends on every chunk's
char_start/char_end still pointing at the right place in the original text
after wrap-rejoining. If those drift, the highlight feature silently lies.
"""

from __future__ import annotations

import pytest

from services.matching.chunking import (
    ChunkedDocument,
    ChunkKind,
    Emphasis,
    chunk_job_description,
    chunk_resume,
    normalize_document_text,
    prepare_resume,
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

    def test_title_case_job_titles_are_not_misclassified_as_headings(self):
        # Title Case used to be accepted as a third heading path (alongside
        # vocab and ALL CAPS). Too loose against real documents: a job
        # title is Title Case too, and isn't a section boundary.
        text = (
            "Senior Backend Engineer\n"
            "Built distributed systems at scale.\n\n"
            "React Native Developer\n"
            "Shipped mobile apps used by millions.\n"
        )
        chunks = chunk_resume(text)
        assert all(c.kind is not ChunkKind.HEADING for c in chunks)

    def test_job_titles_matching_a_topic_word_are_still_not_headings(self):
        # The topic-token segmentation path below (Leadership / Extracurricular)
        # is deliberately broader than exact vocab -- broad enough that a bare
        # word like "project" (from _SECTION_VOCAB's "projects") or "research"
        # would otherwise catch job titles that happen to contain it. The
        # _ROLE_NOUN_TOKENS veto exists specifically for this.
        text = (
            "Project Manager\n"
            "Ran cross-functional projects end to end.\n\n"
            "Research Assistant\n"
            "Supported faculty research.\n"
        )
        chunks = chunk_resume(text)
        assert all(c.kind is not ChunkKind.HEADING for c in chunks)

    def test_unrecognized_compound_heading_still_ends_the_section(self):
        # The actual bug this fixes: a heading the vocabulary doesn't know
        # ("Leadership / Extracurricular") used to fail _is_heading entirely,
        # so nothing flushed the buffer or updated `section` -- everything
        # under it stayed silently tagged with the prior section. Not
        # knowing the heading's canonical name is fine; not knowing it's a
        # boundary at all is the corruption. Segmentation must fire even
        # when classification can't name the section.
        text = (
            "TECHNICAL SKILLS\n"
            "Python, Docker, Kubernetes\n\n"
            "Leadership / Extracurricular\n"
            "President University Name\n"
            "- Achieved a 4 star fraternity ranking\n"
            "- Managed executive board of 5 members\n"
        )
        chunks = chunk_resume(text)
        heading = next(c for c in chunks if "Leadership" in c.text)
        assert heading.kind is ChunkKind.HEADING
        bullets = [c for c in chunks if c.kind is ChunkKind.BULLET]
        assert len(bullets) == 2
        assert all(b.section == "leadership / extracurricular" for b in bullets)
        # Specifically: NOT stuck on the prior "technical skills" section,
        # which is what silently excluded these as skills-section noise.
        assert all(b.section != "technical skills" for b in bullets)


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

    def test_mojibake_bullet_is_not_recognized_without_normalizing_first(self):
        # The precondition is real, not just documented: chunk_resume alone
        # does not fix mojibake. If this ever starts passing, chunk_document
        # has silently regained an internal ftfy call, which reopens the
        # canonical-text problem the module docstring explains.
        mojibake_bullet = "•".encode("utf-8").decode("cp1252")
        text = f"{mojibake_bullet} Built the ingestion service\n"
        chunks = chunk_resume(text)
        assert chunks[0].kind is not ChunkKind.BULLET

    def test_mojibake_bullets_are_recovered_after_normalizing(self):
        # A UTF-8 bullet (E2 80 A2) mis-decoded as cp1252 becomes three
        # characters, not one -- constructed here rather than pasted, since
        # mojibake is exactly the kind of text that doesn't survive copy
        # -paste intact. Real source: PDFs exported from Word on Windows.
        mojibake_bullet = "•".encode("utf-8").decode("cp1252")
        assert len(mojibake_bullet) == 3  # the failure mode being tested

        text = f"{mojibake_bullet} Built the ingestion service\n"
        canonical = normalize_document_text(text)
        chunks = chunk_resume(canonical)
        assert len(chunks) == 1
        assert chunks[0].kind is ChunkKind.BULLET
        assert chunks[0].text == "Built the ingestion service"

        # Offsets are relative to the canonical (normalized) text, not the
        # raw input -- see chunking.py's module docstring. Like other
        # BULLET chunks, the span covers the whole original line (glyph
        # included); only `.text` has the glyph stripped -- same convention
        # as test_offsets_point_into_the_original_text above.
        c = chunks[0]
        assert "Built" in canonical[c.char_start : c.char_end]

    def test_prepare_resume_bundles_canonical_text_with_chunks(self):
        mojibake_bullet = "•".encode("utf-8").decode("cp1252")
        text = f"{mojibake_bullet} Built the ingestion service\n"

        doc = prepare_resume(text)
        assert isinstance(doc, ChunkedDocument)
        assert doc.canonical_text == normalize_document_text(text)
        assert len(doc.chunks) == 1
        assert doc.chunks[0].kind is ChunkKind.BULLET
        # The whole point: chunk offsets are valid against canonical_text.
        c = doc.chunks[0]
        assert "Built" in doc.canonical_text[c.char_start : c.char_end]


class TestScorableFloor:
    def test_terse_jd_bullets_survive(self):
        """Stack lists are requirements, not noise.

        A blanket three-word floor dropped every one of these silently --
        found via the scoring service, not by reading the chunker.
        """
        jd = "Requirements\n\n• Java\n• Spring Boot\n• MySQL\n"
        scorable = [c.text for c in chunk_job_description(jd) if c.is_scorable]
        assert scorable == ["Java", "Spring Boot", "MySQL"]

    def test_one_word_resume_fragments_are_still_noise(self):
        resume = "EXPERIENCE\n\n• Shipped\n• Built a FastAPI service in Python\n"
        scorable = [c.text for c in chunk_resume(resume) if c.is_scorable]
        assert scorable == ["Built a FastAPI service in Python"]

    def test_terse_resume_skills_section_survives(self):
        """The same stack-list style is just as common on the resume side,
        under a Skills heading -- the floor shouldn't drop those either.
        """
        resume = "SKILLS\n\n• Python\n• Docker\n• Kubernetes\n"
        scorable = [c.text for c in chunk_resume(resume) if c.is_scorable]
        assert scorable == ["Python", "Docker", "Kubernetes"]

    def test_terse_floor_relief_is_scoped_to_the_skills_section_only(self):
        # A one-word bullet outside Skills is still noise, even in the same
        # document that has a terse Skills section.
        resume = (
            "SKILLS\n\n• Python\n• Docker\n\n"
            "EXPERIENCE\n\n• Shipped\n• Built a FastAPI service in Python\n"
        )
        chunks = {c.text: c.is_scorable for c in chunk_resume(resume) if c.kind is ChunkKind.BULLET}
        assert chunks == {
            "Python": True,
            "Docker": True,
            "Shipped": False,
            "Built a FastAPI service in Python": True,
        }
