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
offsets survive every transformation from here on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

# Bullet glyphs seen in real PDF extractions, including the 'o' that Word
# emits for second-level bullets. Does NOT handle mis-decoded (mojibake)
# bullets from a cp1252/Latin-1 misread of UTF-8 -- no test exercises that
# case yet, and guessing at the byte pattern without one would be worse
# than leaving it undone. Flagged as a known gap, not silently absent.
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

    @property
    def is_scorable(self) -> bool:
        return (
            self.kind is not ChunkKind.HEADING
            and self.emphasis is not Emphasis.BOILERPLATE
            and len(self.text.split()) >= 3
        )


def _is_heading(line: str) -> bool:
    """Headings are short, unpunctuated, and usually shouty."""
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
    # ALL CAPS
    if stripped.isupper():
        return True
    # Title Case: every substantive word capitalised. Commas rule it out --
    # "Python, FastAPI, PostgreSQL, Docker" is a skills line, not a heading.
    if "," in stripped:
        return False
    return all(w[0].isupper() for w in words if len(w) > 3) and words[0][0].isupper()


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
    """Split a resume or JD into units, preserving offsets into ``text``."""
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
    """Chunk a JD and tag each unit with its emphasis."""
    return [
        Chunk(
            text=c.text, kind=c.kind, section=c.section,
            char_start=c.char_start, char_end=c.char_end,
            index=c.index, emphasis=classify_emphasis(c),
        )
        for c in chunk_document(text)
    ]


def chunk_resume(text: str) -> list[Chunk]:
    """Chunk a resume. Emphasis is not meaningful here, so it stays unset."""
    return chunk_document(text)
