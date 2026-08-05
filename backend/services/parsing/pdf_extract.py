"""PDF text extraction with word-level coordinates, column detection, and
reading-order reconstruction.

Replaces services/parser.py's ``PyPDF2.extract_text()``, which sorts
words by whatever order they appear in the PDF's content stream. That
order has no guaranteed relationship to visual reading order -- some
generators happen to draw column-by-column (so it looks fine), most
don't. Verified against a real Canva export in test_corpus/: job titles,
companies, and dates end up in three unrelated clusters, completely
disconnected from each other ("HCL Technologies" / "AI/ML Intern" /
"Pinfinity Foundation" / "Full Stack Developer Intern" all adjacent, with
"Expected June 2027" and "Sultanpur, UP" nowhere near the job they belong
to). This is not a rare edge case -- two-column and sidebar résumé
templates are extremely common.

pdfplumber's own ``page.extract_text()`` isn't the fix either: it sorts by
geometric position (top, then x0) across the *whole page width*, which
interleaves two side-by-side columns into a similar mess, just a
differently-shaped one.

The actual fix needs three things from the same pass over word
coordinates:

1. **Column detection** (`detect_columns`): find vertical gutters -- bands
   of the page where no word ever draws, wide enough and positioned
   inside the content area (not just a margin) to be a real column split,
   not a coincidental gap in one line.
2. **Column assignment**: each word belongs to whichever column its
   horizontal center falls into.
3. **Reading order** (`reading_order`): read column 0 top-to-bottom
   (grouping words into lines by matching `top`), then column 1, etc.

A page with no extractable words at all (`page.extract_words()` returns
nothing) is flagged as a warning rather than silently producing an empty
string -- confirmed on a real batch of 12 gathered files that all turned
out to be scanned images with zero text layer (`len(page.chars) == 0`,
one full-page image). Silently scoring an empty resume as "0% match" is a
worse failure than saying so.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

import pdfplumber

# A gutter must be at least this fraction of page width to count as a real
# column split, not noise from natural word/letter spacing.
_MIN_GAP_FRACTION = 0.03
# Neither resulting column may be narrower than this fraction of the page --
# guards against a near-page-edge gap (e.g. a decorative rule) being read as
# a column split that would leave one "column" a sliver.
_MIN_COLUMN_FRACTION = 0.15
# Words within this many points of vertical position are treated as being
# on the same line.
_LINE_TOLERANCE = 3.0
_HIST_BINS = 200

# Readability gate. Calibrated against the real corpus, not guessed: every
# genuinely text-based résumé measured (5 real, 5 synthetic) landed between
# 1254 and 3805 chars/page; every one of 12 confirmed-scanned files landed
# at exactly 0. There is no ambiguous middle ground in that data, so this
# threshold has enormous margin on both sides rather than being tuned to a
# knife's edge.
MIN_CHARS_PER_PAGE = 50


@dataclass(frozen=True, slots=True)
class Word:
    text: str
    x0: float
    x1: float
    top: float
    bottom: float
    page: int


@dataclass(frozen=True, slots=True)
class PageInfo:
    page: int
    width: float
    height: float
    column_bounds: list[tuple[float, float]]
    has_text_layer: bool


@dataclass
class ExtractionResult:
    text: str
    words: list[Word] = field(default_factory=list)
    pages: list[PageInfo] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def column_counts(self) -> list[int]:
        return [len(p.column_bounds) for p in self.pages]

    @property
    def chars_per_page(self) -> float:
        return len(self.text) / len(self.pages) if self.pages else 0.0

    @property
    def is_readable(self) -> bool:
        """False for a scanned/image-only PDF (or any other cause of a
        near-empty text layer) -- see MIN_CHARS_PER_PAGE for calibration.
        """
        return self.chars_per_page >= MIN_CHARS_PER_PAGE

    @property
    def parse_status(self) -> str:
        return "ok" if self.is_readable else "unreadable"


def _histogram_ink(words: list[Word], page_width: float, n_bins: int = _HIST_BINS) -> list[int]:
    """Count words whose horizontal span overlaps each x-axis bin.

    Uses the word's full [x0, x1] span, not just its left edge -- a single
    word or line spanning a candidate gutter is proof that gap isn't a real
    column split, even if most other lines don't cross it.
    """
    bins = [0] * n_bins
    bin_width = page_width / n_bins
    if bin_width <= 0:
        return bins
    for w in words:
        start = max(0, int(w.x0 / bin_width))
        end = min(n_bins - 1, int(w.x1 / bin_width))
        for b in range(start, end + 1):
            bins[b] += 1
    return bins


def detect_columns(words: list[Word], page_width: float) -> list[tuple[float, float]]:
    """Find column boundaries as [(x_start, x_end), ...], left to right.

    Returns a single (0, page_width) span when no real gutter is found.
    Only ever splits into two columns -- three-plus-column résumés are
    rare enough that a wrong 3-way split is a worse bet than a
    conservative 2-way one; revisit if the corpus shows otherwise.
    """
    if not words:
        return [(0.0, page_width)]

    bins = _histogram_ink(words, page_width)
    bin_width = page_width / len(bins)

    zero_runs: list[tuple[int, int]] = []
    start: int | None = None
    for i, count in enumerate(bins):
        if count == 0:
            start = i if start is None else start
        elif start is not None:
            zero_runs.append((start, i))
            start = None
    if start is not None:
        zero_runs.append((start, len(bins)))

    min_gap_bins = max(1, int(_MIN_GAP_FRACTION * len(bins)))
    # Runs touching bin 0 or the last bin are page margins, not gutters.
    candidates = [
        (s, e) for s, e in zero_runs
        if (e - s) >= min_gap_bins and s > 0 and e < len(bins)
    ]
    if not candidates:
        return [(0.0, page_width)]

    gap_start, gap_end = max(candidates, key=lambda se: se[1] - se[0])
    gap_center = (gap_start + gap_end) / 2 * bin_width

    left_width, right_width = gap_center, page_width - gap_center
    if left_width < _MIN_COLUMN_FRACTION * page_width or right_width < _MIN_COLUMN_FRACTION * page_width:
        return [(0.0, page_width)]

    return [(0.0, gap_center), (gap_center, page_width)]


def _column_index(word: Word, column_bounds: list[tuple[float, float]]) -> int:
    mid = (word.x0 + word.x1) / 2
    for i, (lo, hi) in enumerate(column_bounds):
        if lo <= mid < hi:
            return i
    return len(column_bounds) - 1


def reading_order(words: list[Word], column_bounds: list[tuple[float, float]]) -> list[list[Word]]:
    """Group words into lines, in reading order: column 0 top-to-bottom,
    then column 1 top-to-bottom, etc. Each returned line is itself ordered
    left-to-right.
    """
    by_column: dict[int, list[Word]] = defaultdict(list)
    for w in words:
        by_column[_column_index(w, column_bounds)].append(w)

    lines: list[list[Word]] = []
    for col in sorted(by_column):
        col_words = sorted(by_column[col], key=lambda w: (w.top, w.x0))
        current: list[Word] = []
        for w in col_words:
            if current and abs(current[0].top - w.top) > _LINE_TOLERANCE:
                lines.append(sorted(current, key=lambda cw: cw.x0))
                current = []
            current.append(w)
        if current:
            lines.append(sorted(current, key=lambda cw: cw.x0))
    return lines


def extract_document(pdf_bytes_or_path) -> ExtractionResult:
    """Extract text from a PDF, column-aware, with parse-safety warnings."""
    all_words: list[Word] = []
    pages: list[PageInfo] = []
    text_lines: list[str] = []
    warnings: list[str] = []

    with pdfplumber.open(pdf_bytes_or_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            raw_words = page.extract_words(keep_blank_chars=False)
            words = [
                Word(text=w["text"], x0=w["x0"], x1=w["x1"], top=w["top"], bottom=w["bottom"], page=page_num)
                for w in raw_words
            ]

            if not words:
                has_images = len(page.images) > 0
                reason = "likely scanned (image, no text layer)" if has_images else "blank or unreadable encoding"
                warnings.append(f"page {page_num}: no extractable text -- {reason}")
                pages.append(PageInfo(
                    page=page_num, width=page.width, height=page.height,
                    column_bounds=[(0.0, page.width)], has_text_layer=False,
                ))
                continue

            bounds = detect_columns(words, page.width)
            if len(bounds) > 1:
                warnings.append(f"page {page_num}: {len(bounds)} columns detected")
            pages.append(PageInfo(
                page=page_num, width=page.width, height=page.height,
                column_bounds=bounds, has_text_layer=True,
            ))

            all_words.extend(words)
            for line in reading_order(words, bounds):
                text_lines.append(" ".join(w.text for w in line))

    return ExtractionResult(
        text="\n".join(text_lines),
        words=all_words,
        pages=pages,
        warnings=warnings,
    )


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Drop-in replacement for services/parser.py's function of the same
    name: same signature and return type, column-aware extraction inside.
    """
    import io

    return extract_document(io.BytesIO(file_bytes)).text
