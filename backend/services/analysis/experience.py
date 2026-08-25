"""Experience-section structured extraction: org, title, location, dates,
per entry, plus a resume-wide reverse-chronological order check.

Phase 1 item 1. The rubric's own definition of this dimension is mechanical,
not semantic: "org name, job title, city/state, dates on every position,
reverse-chronological order." Five checkable facts (four per-entry, one
resume-wide), not a judgment about whether the experience itself is any
good -- that's what AchievementsScorer and RelevanceScorer are for. This
module only answers "is the structure there," the same way check_sections
only answers "is the heading there."

The previous ExperienceScorer (see scorers.py's git history) scored volume
(bullet count, entry count) because no rubric-shaped implementation existed
yet -- not because volume was believed to be the right proxy. This replaces
it entirely.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from itertools import groupby

from services.matching.chunking import Chunk, ChunkKind

# A header line ("Google Verily Aug. 2018 - Sept. 2019", "Data Scientist
# San Francisco, CA") is short and doesn't contain an internal sentence
# break. This exists to reject PROSE chunks that are actually a bullet's
# wrapped continuation line that the chunker's own continuation heuristic
# (chunking.py's _continues) failed to reattach -- which happens when the
# wrapped line happens to start with a capitalized word ("Team following
# merger. Completed full integration...", a real example from the eval
# corpus: the continuation of a bullet about a merger integration, wrongly
# split into its own PROSE chunk because "Team" is capitalized).
# Mid-sentence punctuation is the tell: a real header line is a label, not
# a sentence, so it never contains "word. Word" internally, and -- a
# second real corpus case (R10: "Analyzed campaign performance and
# prepared reports." misclassified as a header line, apparently a bullet
# that lost its marker glyph during extraction) -- it never TERMINATES in
# sentence punctuation either. A label doesn't end with a period; an
# accomplishment statement almost always does.
#
# The lookbehind requires 2+ letters immediately before the punctuation so
# a title abbreviation ("U.S. Economist, Associate Director," a real R22
# header line) isn't mistaken for a sentence break -- "S." in "U.S." is
# preceded by a single letter, not a word, and doesn't match.
_MID_SENTENCE_BREAK = re.compile(r"(?<=[a-zA-Z]{2})[.!?]\s+[A-Z]")
_HEADER_MAX_WORDS = 14

# Literal, unfilled "Lorem ipsum dolor sit amet..." placeholder text --
# real in the corpus (R10, R14: both Canva-style templates where the
# experience section's body was never replaced with actual content, and
# both drew a low human score, 7/20 and 4/20, for exactly that reason).
# Checking for this fixed, well-known Latin phrase is a mechanical
# string match, not a semantic judgment of content quality -- it's the
# same kind of check as _FACT_LISTING_PATTERN, just catching "this isn't
# real information" instead of "this isn't an achievement claim." Without
# it, a lorem-ipsum line's leftover words after date/location stripping
# still read as plausible "org name" residual text, silently crediting a
# template that was never filled in.
_LOREM_IPSUM_PATTERN = re.compile(r"lorem ipsum|dolor sit amet|consectetur adipiscing", re.IGNORECASE)


def _is_header_shaped(text: str) -> bool:
    words = text.split()
    if not words or len(words) > _HEADER_MAX_WORDS:
        return False
    if text.rstrip().endswith((".", "!", "?")):
        return False
    return not _MID_SENTENCE_BREAK.search(text)


_MONTH = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t|tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?"
)
# "20XX" is this corpus's own anonymization placeholder for a real year
# (see evaluation/step0's synthetic-identity resumes) -- treated as a valid
# year token for presence detection, though it can't be compared for
# ordering (see _entry_order_rank).
_YEAR = r"(?:\d{4}|20XX)"
_PRESENT = r"(?:Present|Current|Now)"
_DATE_TOKEN = rf"(?:{_MONTH}\s+)?{_YEAR}"
DATE_PATTERN = re.compile(rf"{_DATE_TOKEN}|{_PRESENT}", re.IGNORECASE)

# US state abbreviations + DC/Remote: a precise, low-false-positive
# pattern, safe to use for both presence detection and for stripping
# location text out when looking for residual org content (see
# ExperienceEntry.facts).
_STATE_ABBR = (
    "AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|"
    "MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|"
    "WA|WV|WI|WY|DC"
)
LOCATION_PATTERN = re.compile(rf",\s*(?:{_STATE_ABBR}\b|D\.?C\.?\b|Remote\b)")

# A comma followed by a Title-Case word/short phrase also covers
# non-US locations ("Paris, France" -- the corpus isn't US-only, R29 is
# internationally set) that the state-abbreviation pattern above can't
# catch. Kept separate from LOCATION_PATTERN, and only used for presence
# detection (never for stripping org-residual text), because on its own
# it's too promiscuous: "Acme Corp, Analyst, 2023-2024" would otherwise
# read "Analyst" as a location. _has_location vetoes any match against
# _TITLE_PATTERN below before counting it.
_LOCATION_GENERIC_PATTERN = re.compile(r",\s*([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\b")

# Curated from common resume job-title vocabulary, checked against the
# eval corpus's real title lines (see the module-level calibration notes
# in ExperienceScorer). Broader than chunking.py's _ROLE_NOUN_TOKENS
# (which exists for a different purpose -- vetoing false section-heading
# matches, not identifying titles) because a false negative here directly
# costs a resume real points, so it's worth being generous.
_TITLE_KEYWORDS = (
    "manager", "engineer", "developer", "analyst", "scientist", "specialist",
    "coordinator", "assistant", "associate", "consultant", "director",
    "administrator", "officer", "intern", "president", "treasurer",
    "secretary", "chair", "researcher", "architect", "technician",
    "designer", "representative", "supervisor", "founder", "advisor",
    "fellow", "editor", "writer", "producer", "recruiter", "strategist",
    "lead", "head", "chief", "senior", "junior", "vp", "vice president",
    "ceo", "cfo", "coo", "cto", "auditor", "accountant", "attorney",
    "paralegal", "nurse", "physician", "teacher", "professor", "instructor",
    # Second tier, added after measuring real title lines the first list
    # missed across the eval corpus -- mostly campus/non-profit/service
    # roles ("Peer Mentor," "Camp Counselor," "Student Educator,"
    # "Advertising Account Executive") that a corporate/tech-skewed list
    # doesn't cover but are exactly as real a "job title" as any of the
    # above.
    "mentor", "educator", "counselor", "tutor", "ambassador", "executive",
    "volunteer", "captain", "editor-in-chief", "trainer", "organizer",
    "chairperson", "member", "liaison",
)
_TITLE_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(w) for w in _TITLE_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


def _has_location(text: str) -> bool:
    if LOCATION_PATTERN.search(text):
        return True
    return any(
        not _TITLE_PATTERN.search(m.group(1))
        for m in _LOCATION_GENERIC_PATTERN.finditer(text)
    )


@dataclass
class ExperienceEntry:
    header_lines: list[str] = field(default_factory=list)
    bullets: list[Chunk] = field(default_factory=list)

    @property
    def header_text(self) -> str:
        return " | ".join(self.header_lines)

    def facts(self) -> dict[str, bool]:
        """The four per-entry checkable facts. See module docstring."""
        has_dates = bool(DATE_PATTERN.search(self.header_text))
        has_location = _has_location(self.header_text)
        has_title = False
        has_org = False
        for line in self.header_lines:
            if _LOREM_IPSUM_PATTERN.search(line):
                # Unfilled template text -- see _LOREM_IPSUM_PATTERN's
                # docstring. Contributes to nothing; without this a
                # "Lorem ipsum dolor sit amet..." line's leftover words
                # fall straight through to the org branch below and get
                # credited as a plausible org name.
                continue
            if _TITLE_PATTERN.search(line):
                has_title = True
                continue
            # Not a title line -- does it carry real content beyond a bare
            # date/location (i.e. plausibly the org name)?
            residual = DATE_PATTERN.sub("", line)
            residual = LOCATION_PATTERN.sub("", residual)
            if len(residual.split()) >= 1:
                has_org = True
        return {"org": has_org, "title": has_title, "location": has_location, "dates": has_dates}


def group_chunks_by_section(chunks: list[Chunk]) -> list[list[Chunk]]:
    """Split a chunk stream into contiguous runs sharing the same raw
    section label, preserving document order.

    Matters for the order check specifically: a resume with both a
    "Non-Profit Experience" heading and a separate "Leadership Experience"
    heading (a real case in the eval corpus, R07) is two independently
    ordered listings, not one. Comparing the last Non-Profit entry against
    the first Leadership entry as if they belonged to a single
    reverse-chronological sequence produced a false violation -- a human
    reading two separately-labeled sections doesn't expect them to
    interleave by date. Per-entry completeness doesn't have this problem
    (it doesn't care which section an entry came from), so only the order
    check needs section-scoped grouping; entry extraction itself doesn't.
    """
    return [list(group) for _, group in groupby(chunks, key=lambda c: c.section)]


# A "header-shaped" PROSE chunk still isn't necessarily a real entry --
# _is_header_shaped only rejects long sentence-like fragments, so a short
# one-off fragment ("Team.", a single replacement-character glyph left
# over from an unresolved encoding issue) still passes it and would
# otherwise open a phantom entry with no real content. An entry earns a
# place in the output only if it has a real bullet, or a header block
# substantial enough to plausibly be an org+title pair rather than
# leftover noise -- checked against the corpus: every genuine 0-bullet
# entry (e.g. R34's "Incoming Summer Analyst," listed with an offer date
# but no bullets yet) clears this by a wide margin (its header alone is
# 15+ words); the garbage fragments this filters out are 1-4 words.
_MIN_NOISE_FILTER_HEADER_WORDS = 4


def _entry_has_real_content(entry: ExperienceEntry) -> bool:
    if entry.bullets:
        return True
    real_lines = [line for line in entry.header_lines if not _LOREM_IPSUM_PATTERN.search(line)]
    return sum(len(line.split()) for line in real_lines) >= _MIN_NOISE_FILTER_HEADER_WORDS


def extract_experience_entries(chunks: list[Chunk]) -> list[ExperienceEntry]:
    """Group an experience-section chunk stream into per-role entries.

    `chunks` should already be filtered to the resume's experience-labeled
    section(s), in document order, BULLET and PROSE only (no HEADING).

    Segmentation rule, derived from real formatting across the eval corpus
    (see the module docstring for the two shapes it has to handle):
    a new entry starts whenever a header-shaped PROSE line follows a
    BULLET (the previous role's bullets just ended), or whenever a header
    block would exceed two lines (real entries use at most an org line and
    a title line -- a third consecutive header-shaped line, with no bullet
    in between, has to belong to the next entry). This correctly separates
    back-to-back entries that have no bullets between them at all (a real
    case in the corpus: an "Incoming Summer Analyst" role listed with a
    date but zero bullets, immediately followed by the next employer's
    header) without being fooled by a misclassified bullet-continuation
    fragment landing between two entries (also real -- see
    _is_header_shaped's docstring).

    Entries with no bullets and a near-empty header (see
    _entry_has_real_content) are dropped before returning -- they're
    parsing noise (a stray one-word fragment slipping past
    _is_header_shaped), not real positions a human grader would ever see
    or judge for completeness.
    """
    entries: list[ExperienceEntry] = []
    current: ExperienceEntry | None = None
    header_count = 0
    just_saw_bullet = False

    for chunk in chunks:
        if chunk.kind is ChunkKind.BULLET:
            if current is None:
                current = ExperienceEntry()
                entries.append(current)
            current.bullets.append(chunk)
            just_saw_bullet = True
        elif chunk.kind is ChunkKind.PROSE:
            if not _is_header_shaped(chunk.text):
                continue
            # A header line ending in a bare dash ("...October 2020-") is a
            # date range the PDF wrapped onto its own line ("December
            # 2020" follows) -- real corpus case (R05). Without this, the
            # 2-line cap below would split it into a phantom entry and
            # misattribute the real entry's bullets to that phantom.
            dangling_range = bool(
                current and current.header_lines
                and current.header_lines[-1].rstrip().endswith(("-", "–", "—"))
            )
            if current is None or just_saw_bullet or (header_count >= 2 and not dangling_range):
                current = ExperienceEntry()
                entries.append(current)
                header_count = 0
            current.header_lines.append(chunk.text)
            header_count += 1
            just_saw_bullet = False
        # HEADING chunks aren't expected in this stream; ignored if present.

    return [e for e in entries if _entry_has_real_content(e)]

    return entries


def _entry_order_rank(entry: ExperienceEntry) -> int | None:
    """A comparable "how recent" rank for reverse-chronological ordering,
    keyed on START year, not end year.

    Tried end-year first (with "Present" as a sentinel "most recent"
    value) and found a real false positive: R34's "Lead Research
    Assistant, January 2021-Present" (still ongoing) was flagged as
    out-of-order for appearing after "Corporate Finance Intern, June
    2021-August 2021" (already ended) -- correct under an end-date
    convention, but resumes are conventionally ordered by when a role
    STARTED, not by whether it happens to still be open; ranking both by
    start year (2021 vs. 2021, tied) shows no violation, which matches how
    a human reads this resume. Re-checked the one genuine violation this
    module does flag (R16: a still-ongoing "Present" role listed last,
    after two already-ended roles that both started earlier) under both
    conventions -- it's a real violation either way, so switching to
    start-year cost nothing there.

    None means unparseable/ambiguous (e.g. every date in this corpus's
    synthetic identities is literally the placeholder "20XX," which can't
    be compared against another "20XX") -- callers must skip, not fail,
    pairs where either side is None.
    """
    years = re.findall(r"\d{4}", entry.header_text)
    if years:
        return int(years[0])
    return None


def check_reverse_chronological_order(entries: list[ExperienceEntry]) -> tuple[bool, int, int]:
    """(order_ok, comparable_pairs, violations) across consecutive entries
    WITHIN one listing.

    Callers should only pass entries drawn from a single section run (see
    group_chunks_by_section) -- comparing across two independently-labeled
    listings ("Non-Profit Experience" vs. "Leadership Experience")
    produces a false violation; see that function's docstring.

    order_ok is True whenever zero violations are found among comparable
    pairs -- including when there are zero comparable pairs at all (e.g. a
    single-entry resume, or a corpus whose dates are all the "20XX"
    placeholder). Absence of evidence of a violation is treated as the
    check passing, not as uncomputable: the per-entry completeness score
    already penalizes missing/unparseable dates on their own account, so
    this doesn't additionally penalize a resume twice for the same missing
    information.
    """
    ranks = [_entry_order_rank(e) for e in entries]
    comparable = 0
    violations = 0
    for prev, nxt in zip(ranks, ranks[1:]):
        if prev is None or nxt is None:
            continue
        comparable += 1
        if nxt > prev:
            violations += 1
    return violations == 0, comparable, violations


def extract_all_experience_entries(chunks: list[Chunk]) -> tuple[list[ExperienceEntry], bool, int, int]:
    """The one call ExperienceScorer needs: entries pooled across every
    section run (for completeness scoring, which doesn't care about
    section boundaries), plus an order check aggregated section-by-section
    (which does -- see group_chunks_by_section).

    Returns (all_entries, order_ok, comparable_pairs, violations).
    """
    all_entries: list[ExperienceEntry] = []
    comparable_total = 0
    violations_total = 0
    for section_chunks in group_chunks_by_section(chunks):
        section_entries = extract_experience_entries(section_chunks)
        all_entries.extend(section_entries)
        _, comparable, violations = check_reverse_chronological_order(section_entries)
        comparable_total += comparable
        violations_total += violations
    return all_entries, violations_total == 0, comparable_total, violations_total
