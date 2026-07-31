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
_BULLET = re.compile(r"^\s*(?:[•‣▪●◦⁃∙*\-–—]|o(?=\s)|\d{1,2}[.)])\s+")
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
_SKILLS_SECTION_NAMES = frozenset({"skills", "technical skills", "core competencies", "technologies"})
_REQUIRED_CUES = ("must have", "required", "requirement", "you have", "you will need",
                  "we require", "essential", "minimum", "at least", "proven")
_PREFERRED_CUES = ("nice to have", "preferred", "bonus", "plus", "desirable",
                   "advantage", "good to have", "ideally")
_BOILERPLATE_CUES = ("we are a", "we're a", "about us", "our mission", "equal opportunity",
                     "benefits include", "apply now", "join us", "who we are",
                     "salary", "perks", "we offer")


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
        # _SKILLS_SECTION_NAMES above.
        floor = 1 if self.section in _SKILLS_SECTION_NAMES else self.min_words
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
    exercised. A heading now requires *known* section vocabulary or ALL
    CAPS -- nothing else. Costs some recall on unusual heading styles
    (rare, and a false negative here just leaves a heading classified as
    prose, which is a much smaller error than fabricating a false section
    boundary).
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
    return stripped.isupper()


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
