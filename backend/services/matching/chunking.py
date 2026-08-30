"""Chunking: turn raw resume and JD text into the units retrieval operates on.

This is the layer everything in Phase 2 sits on, and it is the layer most
likely to be quietly wrong. Embedding quality is bounded by chunk quality --
a bi-encoder cannot recover from a bullet that got split in half by a PDF
line wrap.

Two asymmetric problems:

  resume  Bullets, wrapped across lines by the PDF exporter with no reliable
          terminator. A continuation line has to be rejoined to its bullet or
          you embed sentence fragments.
  JD      Mixed prose and bullets. Requirements need separating from company
          boilerplate ("we're a fast-growing startup..."), and required needs
          separating from preferred, because they should not be weighted the
          same in the final score.

Char offsets are preserved end to end so a match can be highlighted in the
original document. That is the evidence-linking feature -- it only works if
offsets survive every transformation from here on, which is also why
normalization is a separate, explicit step rather than something buried
inside chunking.

`normalize_document_text` repairs mojibake (a UTF-8 bullet mis-decoded as
cp1252 becomes 3 characters instead of 1 -- common on PDFs exported from
Word on Windows) via `ftfy.fix_text`. Because that changes the string's
length, offsets computed by `chunk_document` are only meaningful relative to
already-normalized text -- `chunk_document` therefore *requires* normalized
input (a precondition, not a step it performs) rather than normalizing
internally. Normalizing inside chunking would make it silently safe to call
with raw text once, but silently WRONG the moment any other code
(rendering, highlighting, a second pipeline stage) touches the same
document and doesn't normalize identically -- the raw text and the chunk
offsets would then disagree about what "the document" is, and nothing would
signal the mismatch. Normalize once, at ingestion, treat the result as the
only version of the document that exists from then on. `prepare_resume` /
`prepare_job_description` below do exactly that and hand back the
normalized text bundled with its chunks, so a caller physically cannot have
one without the other.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

import ftfy

# Bullet glyphs seen in real PDF extractions, including the 'o' that Word
# emits for second-level bullets. Mis-decoded (mojibake) bullets are only
# matched after normalize_document_text has already run -- see the module
# docstring.
#
# Public (no leading underscore): anything outside this module that needs
# to recognize "is this line a bullet" (e.g. a test injecting a defect
# into bullet lines specifically) should match against this exact pattern,
# not a hand-copied approximation of it -- a narrower ad-hoc bullet regex
# elsewhere silently missed real bullet glyphs this one already handles
# (confirmed: a defect-injection test using its own "[bullet-dash-star]"
# regex found zero bullets on a resume using "●" bullets, which this
# pattern already recognized).
BULLET = re.compile(r"^\s*(?:[•‣▪●◦⁃∙*\-–—]|o(?=\s)|\d{1,2}[.)])\s+")
_BULLET = BULLET  # internal alias, so every existing in-module reference stays unchanged
_SECTION_VOCAB = {
    "experience", "work experience", "professional experience", "employment",
    "education", "academics", "qualifications",
    "skills", "technical skills", "core competencies", "technologies",
    "projects", "personal projects", "academic projects",
    "certifications", "achievements", "awards", "publications",
    "summary", "objective", "profile", "about",
    "responsibilities", "requirements", "qualifications",
    "activities", "interests", "languages", "contact",
    "nice to have", "preferred qualifications", "what you will do",
    "what we offer", "benefits", "role", "the role",
}
# A resume's own skills section is exactly as terse as a JD's stack list --
# "• Python" / "• Docker" / "• Kubernetes" one-per-bullet is a common resume
# style, not noise. Chunk.min_words's resume default of 3 was written with
# only prose bullets in mind and silently dropped these from scoring on the
# resume side, the same class of bug chunk_job_description's min_words=1
# fixed on the JD side.
#
# Public (no leading underscore): analyzer.py's quantification check also
# needs to recognize skills-section bullets, to exclude them the same way.
SKILLS_SECTION_NAMES = frozenset({"skills", "technical skills", "core competencies", "technologies"})

# A bulleted or prose line that's structurally a label + comma-separated
# list -- "Coursework: Machine Learning, Data Structures, Algorithms",
# "Languages: Written and spoken fluency in Spanish", "Computer skills:
# Excel, Powerpoint, SQL" -- is a fact listing, not prose making a claim
# about anything (an achievement, a writing sample). Originally found and
# fixed in analyzer.py's check_quantification (Phase 1 item 3 follow-up:
# these lines were being counted as ungraded achievement opportunities,
# capping every resume's reachable score well below 100% even for
# genuinely strong ones). Moved here, public, when WritingScorer needed
# the identical exclusion for the identical reason -- a fact-listing line
# isn't real prose to judge for passive voice or filler either, and a
# single shared pattern is safer than two modules independently
# hand-maintaining the same shape (the exact drift risk BULLET's own
# docstring above warns about). NOT applied to skill matching
# (SkillsScorer) -- checked empirically, not assumed: excluding these
# lines from skill extraction loses real, correctly-recognized skills on
# 15/39 corpus resumes (a "Computer skills:" or "Languages:" line is
# exactly where people legitimately declare skills), the opposite of the
# achievements/writing case where the line structurally can't satisfy
# what's being measured.
FACT_LISTING_PATTERN = re.compile(r"^[A-Za-z][A-Za-z /&'-]{1,40}:\s")
_REQUIRED_CUES = ("must have", "required", "requirement", "you have", "you will need",
                  "we require", "essential", "minimum", "at least", "proven")
_PREFERRED_CUES = ("nice to have", "preferred", "bonus", "plus", "desirable",
                   "advantage", "good to have", "ideally")
_BOILERPLATE_CUES = ("we are a", "we're a", "about us", "our mission", "equal opportunity",
                     "benefits include", "apply now", "join us", "who we are",
                     "salary", "perks", "we offer")


def _singularize(word: str) -> str:
    """Crude, inspectable de-pluralization -- not a real stemmer.

    Exists so "Certification" registers against the vocabulary's
    "certifications" without hand-maintaining both forms for every entry.
    Deliberately narrow: it only strips the common English plural suffixes
    and leaves anything it isn't sure about untouched, rather than risk
    mangling a word into a false match.
    """
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith(("ses", "xes", "ches", "shes")):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word


def _heading_topic_tokens(line: str) -> set[str]:
    """Normalize a heading-shaped line into topic tokens for vocabulary matching.

    Splits compound headings ("Leadership / Extracurricular", "Technical &
    Language Skills") on their separators and singularizes each piece, so a
    heading only needs ONE recognized topic word to register -- not an
    exact match on the entire phrase. This is deliberately a weaker test
    than the exact-phrase-or-ALL-CAPS test in _is_heading: it exists only to
    decide segmentation (does this line end the current section?), not
    classification (what IS this section, canonically?) -- see
    _is_heading's docstring for why those two questions are answered
    separately.
    """
    stripped = line.strip().rstrip(":")
    pieces = re.split(r"[,&/]|\band\b|\bof\b", stripped, flags=re.IGNORECASE)
    return {_singularize(w.lower()) for piece in pieces for w in piece.split()}


# Tried auto-deriving this by splitting every _SECTION_VOCAB phrase into
# words -- rejected after a corpus-wide dry run turned up real false
# positives. _SECTION_VOCAB mixes true single-concept nouns ("skills",
# "experience") with idiomatic multi-word JD boilerplate ("what you will
# do", "core competencies", "the role", "nice to have") whose individual
# words are not safe standalone signals: splitting those leaked "the",
# "to", "core", "what", "we" into the topic vocabulary, which matched
# things like "The Tombs, Washington, DC" (an employer name) and "across
# 10 core users" (a bullet fragment) as headings. Hand-curated instead:
# only the words below are individually meaningful enough to end a section
# on their own, each singularized so plural/singular variants both match.
_VOCAB_TOKENS = {
    _singularize(w) for w in (
        "experience", "education", "skills", "certifications",
        "achievements", "awards", "publications", "summary", "objective",
        "activities", "interests", "languages",
    )
}
# "projects" is deliberately excluded despite being in _SECTION_VOCAB: bare
# "project" collided with job titles in the corpus dry run ("Project
# Manager", "Project Coordination", "Project Team Member") that the
# _ROLE_NOUN_TOKENS veto doesn't catch (their second word isn't a role noun
# in every case). Standalone "Projects" / "Personal Projects" / "Academic
# Projects" headings still match today via _SECTION_VOCAB's exact-phrase
# path above, unaffected by this exclusion -- only compound variants this
# corpus never exercised ("Key Projects", "Notable Projects") are missed.

# Sourced externally -- standard resume-section vocabulary from general
# career-services/resume-writing convention, NOT reverse-engineered from any
# specific resume that failed to parse, and trimmed to only the words the
# corpus dry run actually needed plus one safe pairing (extracurricular).
# Several speculative additions (volunteer, tool, research, community,
# training, affiliation, ...) were tried and dropped: each caused a real
# false positive somewhere in the corpus ("Community Volunteer" as a job
# title, "Data Tools"/"Invoicing Tools"/"bioinformatics tools" as skill-list
# items) without fixing anything this eval actually found broken. It's
# expected, not circular, that what's left overlaps with headings the eval
# found unrecognized (leadership, coursework, responsibility, information,
# specialty) -- they were already common resume vocabulary before this
# taxonomy existed; this just catches it up, conservatively.
_EXTRA_HEADING_TOKENS = {
    "leadership", "extracurricular", "coursework", "specialty",
    "responsibility", "information",
}

_HEADING_TOPIC_TOKENS = _VOCAB_TOKENS | _EXTRA_HEADING_TOKENS

# Common occupational nouns. A line whose tokens hit _HEADING_TOPIC_TOKENS
# but ALSO hit this set is a job title ("Project Manager", "Research
# Assistant"), not a section heading -- vetoes the token-overlap path in
# _is_heading. Doesn't need to be exhaustive: false negatives here (a job
# title that slips through) just mean the old behavior for that one line;
# false positives (blocking a genuine heading) are the worse failure mode,
# so this stays conservative rather than trying to be complete.
_ROLE_NOUN_TOKENS = {
    "manager", "engineer", "developer", "analyst", "specialist",
    "coordinator", "assistant", "associate", "consultant", "director",
    "administrator", "officer", "intern", "president", "treasurer",
    "secretary", "chair", "researcher", "architect", "technician",
    "designer", "representative", "supervisor",
}


class ChunkKind(str, Enum):
    BULLET = "bullet"
    PROSE = "prose"
    HEADING = "heading"


class Emphasis(str, Enum):
    """How strongly a JD requirement should count. Required != preferred."""

    REQUIRED = "required"
    PREFERRED = "preferred"
    UNSPECIFIED = "unspecified"
    BOILERPLATE = "boilerplate"


@dataclass(frozen=True, slots=True)
class Chunk:
    text: str
    kind: ChunkKind
    section: str | None
    char_start: int
    char_end: int
    index: int
    emphasis: Emphasis = Emphasis.UNSPECIFIED

    # Minimum words for a chunk to be worth scoring. Asymmetric on purpose:
    # a one-word resume fragment is noise, but a JD bullet that says only
    # "Kubernetes" is a complete requirement. Terse stack lists ("• Java",
    # "• Spring", "• MySQL") are extremely common in job postings, and a
    # blanket three-word floor drops every one of them silently.
    min_words: int = 3

    @property
    def is_scorable(self) -> bool:
        if self.kind is ChunkKind.HEADING or self.emphasis is Emphasis.BOILERPLATE:
            return False
        # Inside a skills section, min_words doesn't apply -- see
        # SKILLS_SECTION_NAMES above.
        floor = 1 if self.section in SKILLS_SECTION_NAMES else self.min_words
        return len(self.text.split()) >= floor


@dataclass(frozen=True, slots=True)
class ChunkedDocument:
    """A document's canonical (normalized) text, bundled with its chunks.

    Exists so a caller cannot end up with chunks whose offsets it can't
    correctly slice into -- `canonical_text` is the *only* text those
    offsets are valid against. Highlighting, storage, and re-display should
    all use `canonical_text`, never whatever raw text the document arrived
    as.
    """

    canonical_text: str
    chunks: list[Chunk]


def normalize_document_text(text: str) -> str:
    """Repair mojibake and other encoding damage. Run this once, at ingestion.

    Not run automatically by chunk_document -- see the module docstring for
    why baking normalization into chunking would be worse than requiring it
    explicitly.
    """
    return ftfy.fix_text(text)


def _is_heading(line: str) -> bool:
    """Headings are short, unpunctuated, and either known vocabulary or shouty.

    Used to also accept generic Title Case ("every substantive word
    capitalised") as a third path. Too loose against real documents: résumé
    lines like "Senior Backend Engineer" or "React Native Developer" are
    Title Case job titles, not section headings, and got misclassified as
    headings on real PDFs in a way the synthetic test fixtures never
    exercised. A heading now requires *known* section vocabulary, ALL CAPS,
    or (see below) a recognized topic token -- nothing else. Costs some
    recall on unusual heading styles (rare, and a false negative here just
    leaves a heading classified as prose, which is a much smaller error
    than fabricating a false section boundary).

    Segmentation vs. classification: the exact-phrase-or-ALL-CAPS check
    above answers "is this a heading, AND do we know what it's called" in
    one step. That conflates two different questions. A heading like
    "Leadership / Extracurricular" or "Positions of Responsibility" fails
    the exact-phrase test (it's not literally in _SECTION_VOCAB) and isn't
    ALL CAPS -- so under the old single-step test it wasn't a heading at
    all, and everything under it stayed tagged with whatever section came
    before. That's the actual corruption (bullets silently misattributed,
    quantification and section-presence scored against the wrong content);
    not knowing the heading's canonical name is a much smaller problem than
    not knowing it's a boundary at all. So: a line that clears the shape
    checks above AND contains at least one recognized topic token (see
    _heading_topic_tokens) is treated as a heading -- ending the section
    it's in, and being scored under check_sections' substring matching --
    even when we can't map it onto a known category. The section label
    stored for what follows it is still just the heading's own raw text
    (unchanged from today), not a canonicalized name; this only fixes WHEN
    the boundary happens, not what to call it.

    Token overlap alone would resurrect the job-title problem above --
    "Project Manager" hits "project" (from _SECTION_VOCAB's "projects"),
    "Research Assistant" would hit "research" if that were in the topic
    vocabulary -- so the topic-token path is vetoed if the line ALSO
    contains a common occupational noun (_ROLE_NOUN_TOKENS). See that set's
    docstring for the residual gap this doesn't close.
    """
    stripped = line.strip().rstrip(":")
    if not stripped or len(stripped) > 40:
        return False
    if _BULLET.match(line):
        return False
    words = stripped.split()
    if len(words) > 4:
        return False
    low = stripped.lower()
    if low in _SECTION_VOCAB:
        return True
    if stripped.endswith((".", ",", ";")):
        return False
    if stripped.isupper():
        return True
    tokens = _heading_topic_tokens(line)
    return bool(tokens & _HEADING_TOPIC_TOKENS) and not (tokens & _ROLE_NOUN_TOKENS)


# Vocab phrases this fix supports are at most 3 words ("nice to have",
# "core competencies", "professional experience"); longest-first so
# "professional experience" wins over a would-be bare "professional" (which
# isn't in _SECTION_VOCAB standalone anyway, but the ordering principle
# matters generally).
_HEADING_PREFIX_LENGTHS = (3, 2, 1)

# See _split_heading_prefix's docstring: every occurrence of these as a
# merge-detected prefix on the 39-resume corpus was a fact-listing
# sub-label ("Languages: English & Spanish", "LANGUAGES Mandarin..."), not
# a genuine section boundary. Excluded from that mechanism specifically,
# not from _SECTION_VOCAB itself -- a standalone "Languages" heading still
# works via _is_heading's exact-line match.
_HEADING_PREFIX_EXCLUDED = frozenset({"languages"})


def _split_heading_prefix(line: str) -> tuple[str, str] | None:
    """Detect "Experience PUTNAM ASSOCIATES BURLINGTON, MA"-style merges:
    a line too long to pass _is_heading's shape gate as a single unit, but
    whose OPENING words are a real, known section heading and whose
    remainder is distinct new content, not a grammatical continuation of
    the heading as a sentence subject.

    Found via R28 in the eval corpus (evaluation/backlog.md's Phase D
    section): its Experience heading merged onto one line with the first
    job entry's company and location, and _is_heading's word-count gate
    rejected the whole 5-word line before ever checking whether it started
    with a recognized heading -- the entire section fell back to
    whatever section preceded it, though the content itself (real company
    names, real bullets) was completely intact. Widening the word limit
    was considered and rejected: it would accept "Skills include Python,
    Docker, and Kubernetes" (6 words) as a heading outright, which is
    wrong in the opposite direction. This function only ever returns a
    split, never a bare "is this a heading" verdict -- segmentation
    (does a boundary exist here) is answered by finding a genuine vocab
    prefix; classification (is the rest of the line real content) is
    answered by requiring it start with a capital letter, distinguishing
    a merged proper-noun entity ("PUTNAM ASSOCIATES") from a lowercase
    grammatical continuation ("include Python...") -- the same
    segmentation-vs-classification split _is_heading's own docstring
    describes, applied one level down: to where the boundary sits WITHIN
    a line, not just whether one exists.

    Deliberately narrow: only exact _SECTION_VOCAB phrases, not the wider
    _HEADING_TOPIC_TOKENS set used elsewhere -- this mechanism is new and
    more permissive in a different way (it fires on lines _is_heading
    would never even look at), so it stays conservative rather than
    compounding two loosened checks together.

    A colon immediately after the prefix vetoes the split -- found on a
    corpus sweep before shipping this, not assumed safe: "Languages:
    English & Spanish fluency" and "Skills: Rhino3D, Adobe Illustrator..."
    both matched the vocab-prefix + capitalized-remainder test (9/9 hits
    on the 39-resume corpus were this pattern, only 1 was R28's genuine
    case) before this guard existed. "Label: comma, separated, list" is a
    fact-listing convention (see FACT_LISTING_PATTERN), not a section
    boundary -- R28's real merge has no colon anywhere near "Experience".
    The colon is the reliable signal telling the two apart, not sentence
    case or word count, which both patterns share.

    "languages" is excluded from the prefix vocabulary here even without
    a colon ("LANGUAGES Mandarin (fluent) Spanish (intermediate)", no
    colon at all) -- also found on the same sweep, sitting between two
    other Skills-adjacent sub-labels ("DESIGN & BUILDING", "RELEVANT
    PROJECT EXPERIENCE" as the actual next section), the same
    fact-listing role as the colon cases, just without the punctuation
    that would have caught it. Every "languages" hit this mechanism has
    produced on this corpus has been this sub-label pattern, never a
    genuine top-level section -- excluded on that evidence, not
    hypothetically. `_is_heading`'s own exact-line match still recognizes
    a standalone "Languages" heading fine; only this more permissive,
    merge-detecting path treats it as unreliable.

    Returns (heading_text, remainder_text) using the line's own
    single-spaced word boundaries -- the caller locates both within the
    original line via string search to preserve char offsets, so this
    stays a pure classification function with no offset bookkeeping of
    its own.
    """
    stripped = line.strip()
    if not stripped or len(stripped) > 60 or _BULLET.match(line):
        return None
    words = stripped.split()
    if len(words) <= 4:
        return None  # _is_heading already handles anything this short
    for plen in _HEADING_PREFIX_LENGTHS:
        if len(words) <= plen:
            continue
        if words[plen - 1].endswith(":"):
            continue  # "Languages: English & Spanish" -- a label, not a merged heading
        prefix_text = " ".join(words[:plen])
        prefix_low = prefix_text.lower().rstrip(":")
        if prefix_low not in _SECTION_VOCAB or prefix_low in _HEADING_PREFIX_EXCLUDED:
            continue
        remainder_text = " ".join(words[plen:])
        if not remainder_text[:1].isupper():
            continue  # "Skills include Python..." -- a sentence, not a merge
        return (prefix_text, remainder_text)
    return None


def _continues(prev: str, line: str) -> bool:
    """Is this line a wrapped continuation of the previous one?

    PDF exporters wrap mid-sentence with no marker. Heuristic: the previous
    line did not end a sentence, and this line does not start a new unit.
    """
    if not prev or _BULLET.match(line) or _is_heading(line):
        return False
    if prev.rstrip().endswith((".", ";", ":", "!", "?")):
        return False
    first = line.lstrip()[:1]
    # A new bullet usually capitalises; a wrap usually does not.
    return bool(first) and (first.islower() or first.isdigit())


def chunk_document(text: str) -> list[Chunk]:
    """Split a resume or JD into units, preserving offsets into ``text``.

    Precondition: ``text`` is already normalized (``normalize_document_text``).
    This function does not normalize -- see the module docstring for why.
    """
    chunks: list[Chunk] = []
    section: str | None = None
    buf: list[str] = []
    buf_start = 0
    offset = 0
    idx = 0

    def flush(end: int) -> None:
        nonlocal buf, idx
        if not buf:
            return
        merged = " ".join(part.strip() for part in buf).strip()
        if merged:
            kind = ChunkKind.BULLET if _BULLET.match(buf[0]) else ChunkKind.PROSE
            body = _BULLET.sub("", merged) if kind is ChunkKind.BULLET else merged
            chunks.append(Chunk(
                text=body.strip(),
                kind=kind,
                section=section,
                char_start=buf_start,
                char_end=end,
                index=idx,
            ))
            idx += 1
        buf = []

    for raw in text.splitlines(keepends=True):
        line = raw.rstrip("\n\r")
        line_start = offset
        offset += len(raw)

        if not line.strip():
            flush(line_start)
            continue

        if _is_heading(line):
            flush(line_start)
            section = line.strip().rstrip(":").lower()
            chunks.append(Chunk(
                text=line.strip(), kind=ChunkKind.HEADING, section=section,
                char_start=line_start, char_end=line_start + len(line), index=idx,
            ))
            idx += 1
            continue

        split = _split_heading_prefix(line)
        if split is not None:
            heading_text, remainder_text = split
            flush(line_start)
            heading_offset = line.index(heading_text)
            heading_start = line_start + heading_offset
            section = heading_text.lower()
            chunks.append(Chunk(
                text=heading_text, kind=ChunkKind.HEADING, section=section,
                char_start=heading_start, char_end=heading_start + len(heading_text), index=idx,
            ))
            idx += 1
            remainder_offset = line.index(remainder_text, heading_offset + len(heading_text))
            buf = [remainder_text]
            buf_start = line_start + remainder_offset
            continue

        if buf and _continues(buf[-1], line):
            buf.append(line)
            continue

        flush(line_start)
        buf = [line]
        buf_start = line_start

    flush(offset)
    return chunks


def classify_emphasis(chunk: Chunk) -> Emphasis:
    """Required / preferred / boilerplate, from cue phrases and section.

    Deliberately rule-based: it is inspectable, costs nothing, and gives the
    eval harness a baseline to beat before anyone reaches for a classifier.
    """
    low = chunk.text.lower()
    if any(cue in low for cue in _BOILERPLATE_CUES):
        return Emphasis.BOILERPLATE
    if any(cue in low for cue in _PREFERRED_CUES):
        return Emphasis.PREFERRED
    if any(cue in low for cue in _REQUIRED_CUES):
        return Emphasis.REQUIRED
    if chunk.section and any(
        w in chunk.section for w in ("prefer", "nice to have", "bonus", "desirable", "good to have")
    ):
        return Emphasis.PREFERRED
    if chunk.section and any(w in chunk.section for w in ("require", "qualification", "responsibilit")):
        return Emphasis.REQUIRED
    return Emphasis.UNSPECIFIED


def chunk_job_description(text: str) -> list[Chunk]:
    """Chunk a JD and tag each unit with its emphasis.

    min_words=1: JD bullets are frequently terse stack lists ("Java",
    "Spring Boot", "MySQL") that are complete requirements on their own --
    see Chunk.min_words.
    """
    return [
        Chunk(
            text=c.text, kind=c.kind, section=c.section,
            char_start=c.char_start, char_end=c.char_end,
            index=c.index, emphasis=classify_emphasis(c),
            min_words=1,
        )
        for c in chunk_document(text)
    ]


def chunk_resume(text: str) -> list[Chunk]:
    """Chunk a resume. Emphasis is not meaningful here, so it stays unset."""
    return chunk_document(text)


def prepare_resume(text: str) -> ChunkedDocument:
    """Normalize, then chunk. The entry point real callers should use."""
    canonical = normalize_document_text(text)
    return ChunkedDocument(canonical_text=canonical, chunks=chunk_resume(canonical))


def prepare_job_description(text: str) -> ChunkedDocument:
    """Normalize, then chunk. The entry point real callers should use."""
    canonical = normalize_document_text(text)
    return ChunkedDocument(canonical_text=canonical, chunks=chunk_job_description(canonical))
