"""Tests for services/analysis/experience.py's structured extraction.

Each test is grounded in a real formatting pattern found in the
39-resume evaluation corpus (see the module's own docstrings for which
resume each guard came from) -- these are regression tests for specific,
previously-real bugs, not speculative edge cases.
"""

from __future__ import annotations

from services.analysis.experience import (
    ExperienceEntry,
    check_reverse_chronological_order,
    extract_all_experience_entries,
    extract_experience_entries,
)
from services.matching.chunking import ChunkKind, chunk_resume, normalize_document_text


def _experience_chunks(text: str):
    chunks = chunk_resume(normalize_document_text(text))
    return [
        c for c in chunks
        if c.kind in (ChunkKind.BULLET, ChunkKind.PROSE) and c.section and "experience" in c.section
    ]


def test_extracts_org_title_location_dates_from_a_two_line_header():
    text = (
        "Experience\n\n"
        "Google Verily Aug. 2018 - Sept. 2019\n"
        "Data Scientist San Francisco, CA\n"
        "- Built ML models to flag early-stage cancer signals\n"
    )
    entries = extract_experience_entries(_experience_chunks(text))
    assert len(entries) == 1
    facts = entries[0].facts()
    assert facts == {"org": True, "title": True, "location": True, "dates": True}


def test_back_to_back_entries_with_no_bullets_between_them_split_correctly():
    # Real case (R34): a role listed with a header and a date but zero
    # bullets, immediately followed by the next employer's header -- no
    # BULLET chunk ever appears between them to signal a boundary.
    text = (
        "Experience\n\n"
        "Morgan Stanley, Sales and Trading New York, NY\n"
        "Incoming Summer Analyst in Fixed Income Division July 2022\n"
        "Ralph Lauren Washington, D.C.\n"
        "Corporate Finance Intern June 2021-August 2021\n"
        "- Collaborated with 5 interns to analyze revenue\n"
    )
    entries = extract_experience_entries(_experience_chunks(text))
    assert len(entries) == 2
    assert entries[0].header_lines == [
        "Morgan Stanley, Sales and Trading New York, NY",
        "Incoming Summer Analyst in Fixed Income Division July 2022",
    ]
    assert entries[0].bullets == []
    assert len(entries[1].bullets) == 1


def test_misclassified_bullet_continuation_fragment_does_not_split_an_entry():
    # Real case (R22): a bullet's wrapped continuation line ("Team
    # following merger. Completed...") starts with a capitalized word, so
    # chunking.py's own continuation heuristic fails to reattach it to the
    # bullet -- it arrives here as a stray PROSE chunk sitting between two
    # real entries. It must not be read as a header line for either one.
    text = (
        "Experience\n\n"
        "AN INVESTMENT BANK, New York, NY, 2018-2019\n"
        "U.S. Economist, Associate Director\n"
        "- Spearheaded integration of people and systems between teams\n"
        "Team following merger. Completed full integration six months early.\n"
        "WORLD BANK, Washington, DC, 2019-2020\n"
        "Research Analyst, Development Economics Research Group\n"
        "- Evaluated capital structure of 4,000 firms\n"
    )
    entries = extract_experience_entries(_experience_chunks(text))
    assert len(entries) == 2
    assert entries[0].header_lines == ["AN INVESTMENT BANK, New York, NY, 2018-2019", "U.S. Economist, Associate Director"]
    assert entries[1].header_lines == ["WORLD BANK, Washington, DC, 2019-2020", "Research Analyst, Development Economics Research Group"]
    assert len(entries[1].bullets) == 1  # not the stray fragment


def test_dangling_date_range_wrapped_onto_its_own_line_stays_with_its_entry():
    # Real case (R05): a PDF-wrapped date range ("...October 2020-" /
    # "December 2020") lands on a third physical line. Without the
    # dangling-range guard the 2-line header cap would split this into a
    # phantom entry and misattribute the real bullets to it.
    text = (
        "Experience\n\n"
        "Senior Design Project, UC Riverside\n"
        "Three-Wheeled Vehicle Design Team Project October 2020-\n"
        "December 2020\n"
        "- Collaborated with 5 engineers to design a vehicle\n"
    )
    entries = extract_experience_entries(_experience_chunks(text))
    assert len(entries) == 1
    assert entries[0].header_lines == [
        "Senior Design Project, UC Riverside",
        "Three-Wheeled Vehicle Design Team Project October 2020-",
        "December 2020",
    ]
    assert len(entries[0].bullets) == 1


def test_lorem_ipsum_placeholder_text_is_not_credited_as_a_real_org():
    # Real case (R10, R14): an unfilled Canva-style template where the
    # experience "description" is literal, un-replaced Lorem Ipsum text.
    text = (
        "Experience\n\n"
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit\n"
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit\n"
    )
    entries = extract_experience_entries(_experience_chunks(text))
    # No real bullets and the header content is entirely placeholder text
    # -- below the noise floor, dropped as not a real entry.
    assert entries == []


def test_stray_short_fragment_does_not_open_a_phantom_entry():
    text = "Experience\n\n•\n- Built a FastAPI service handling 2M requests\n"
    entries = extract_experience_entries(_experience_chunks(text))
    assert len(entries) == 1
    assert len(entries[0].bullets) == 1


def test_order_check_ignores_the_placeholder_year_and_flags_a_real_violation():
    entry_recent_first = ExperienceEntry(header_lines=["Org A, 2022"])
    entry_older = ExperienceEntry(header_lines=["Org B, 2019"])
    entry_placeholder = ExperienceEntry(header_lines=["Org C, 20XX"])

    ok, comparable, violations = check_reverse_chronological_order(
        [entry_recent_first, entry_older, entry_placeholder]
    )
    assert ok and comparable == 1 and violations == 0

    ok, comparable, violations = check_reverse_chronological_order(
        [entry_older, entry_recent_first]
    )
    assert not ok and comparable == 1 and violations == 1


def test_order_check_does_not_compare_across_differently_labeled_sections():
    # Real case (R07): "Non-Profit Experience" and "Leadership Experience"
    # are two independently-ordered listings. The last Non-Profit entry
    # (older) followed by the first Leadership entry (more recent) must
    # not read as a cross-listing violation.
    text = (
        "Non-Profit Experience\n\n"
        "Org A, City, ST 2019\n"
        "- Did a thing\n\n"
        "Leadership Experience\n\n"
        "Org B, City, ST 2020-Present\n"
        "- Did another thing\n"
    )
    entries, order_ok, comparable, violations = extract_all_experience_entries(_experience_chunks(text))
    assert len(entries) == 2
    assert order_ok
    assert comparable == 0  # nothing compared -- different sections


def test_zero_real_entries_is_the_uncomputable_case():
    # Synthetic: a prose-only paragraph under "Experience" with no
    # header-shaped lines and no bullets yields nothing to grade. NOT R28
    # -- that was this test's original claim, and it was wrong (checked
    # directly, not assumed): R28's real failure is a merged heading
    # ("Experience PUTNAM ASSOCIATES BURLINGTON, MA", 5 words, fails the
    # chunker's heading-shape gate), not an absence of bullets -- it has
    # plenty. See scorers.py's ExperienceScorer docstring for the corrected
    # account and services/analysis/scorers.py's _EXPERIENCE_ORDER_WEIGHT
    # comment for where this misattribution also lived.
    text = (
        "Experience\n\n"
        "Developed and implemented a streamlined process for gathering "
        "requirements across several stakeholder teams over the year.\n"
    )
    entries, order_ok, comparable, violations = extract_all_experience_entries(_experience_chunks(text))
    assert entries == []


def test_a_fully_specified_entry_reaches_full_completeness():
    # The ceiling check from Phase 1 item 3 applies here too: a genuinely
    # complete entry must be able to reach 1.0, not be structurally capped
    # below it.
    text = (
        "Experience\n\n"
        "Acme Corp, San Francisco, CA\n"
        "Backend Engineer June 2023 - Present\n"
        "- Built a FastAPI service handling 2M requests per day\n"
    )
    entries = extract_experience_entries(_experience_chunks(text))
    assert len(entries) == 1
    facts = entries[0].facts()
    assert all(facts.values())
