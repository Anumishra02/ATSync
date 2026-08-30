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

import re
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


@dataclass(frozen=True, slots=True)
class LinkAnnotation:
    """A PDF hyperlink annotation (/Annots), not the text layer -- a
    "Watch the demo" link or a LinkedIn icon carries its real target here,
    which page.extract_words() never sees at all. label is best-effort:
    the text-layer words whose bounding box overlaps this annotation's
    rect, joined -- empty when nothing does (an icon/graphic-only link,
    invisible to any text-layer parser, not just this one).
    """

    uri: str
    page: int
    x0: float
    x1: float
    top: float
    bottom: float
    label: str

    @property
    def is_invisible_to_text_layer(self) -> bool:
        return not self.label.strip()


# Loose enough to catch what a résumé author actually types (bare domains,
# no scheme), tight enough not to swallow trailing punctuation/prose.
_URL_IN_TEXT_PATTERN = re.compile(
    r"(?:https?://|www\.)[^\s,;()\[\]<>]+|\b[\w.+-]+@[\w-]+\.[\w.-]+\b"
    r"|\b(?:github|linkedin|gitlab|youtube|behance|gumroad)\.com/[^\s,;()\[\]<>]+",
    re.IGNORECASE,
)


def _normalize_url_fragment(s: str) -> str:
    """Strip scheme/www/mailto and trailing punctuation, lowercase --
    enough to compare a URL as a human typed it in visible text against
    the same URL as it appears in an annotation's URI, which are rarely
    byte-identical (trailing slash, http vs https, www or not).
    """
    s = s.strip().rstrip(".,;:)]}>'\"").lower()
    s = re.sub(r"^mailto:", "", s)
    s = re.sub(r"^https?://", "", s)
    s = re.sub(r"^www\.", "", s)
    return s.rstrip("/")


@dataclass
class ExtractionResult:
    text: str
    words: list[Word] = field(default_factory=list)
    pages: list[PageInfo] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    annotations: list[LinkAnnotation] = field(default_factory=list)

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

    @property
    def text_layer(self) -> str:
        """Explicit name for the channel `.text` already is -- read
        alongside `.annotations` and `.merged` below, not instead of them.
        """
        return self.text

    @property
    def unclickable_urls(self) -> list[str]:
        """URLs/emails written as visible text with no backing annotation
        -- an ATS finding on its own: the applicant TYPED a link but it
        isn't clickable in the PDF (no /Annots entry), so anyone reading
        the PDF itself (not just a text-layer parser) can't click it
        either. Checked via normalized substring match against every
        annotation's URI, not exact equality -- see
        _normalize_url_fragment for why exact match would miss most real
        pairs (http vs https, trailing slash, www or not).
        """
        found_in_text = {m.group(0) for m in _URL_IN_TEXT_PATTERN.finditer(self.text)}
        annotation_fragments = [_normalize_url_fragment(a.uri) for a in self.annotations]
        unclickable = []
        for url in found_in_text:
            frag = _normalize_url_fragment(url)
            if not any(frag in af or af in frag for af in annotation_fragments):
                unclickable.append(url)
        return sorted(unclickable)

    @property
    def invisible_annotations(self) -> list[LinkAnnotation]:
        """Annotations with no text-layer words under their rect -- an
        icon or styled graphic carrying a real link target that any
        text-only parser (this one's own `.text_layer`, or a human
        copy-pasting the résumé's text) cannot see at all.
        """
        return [a for a in self.annotations if a.is_invisible_to_text_layer]

    @property
    def merged(self) -> str:
        """`.text_layer` plus a recovered listing of links the text layer
        alone would never surface -- the real, addressable output of this
        module's third channel, not a placeholder. Deliberately appended
        as a labeled block rather than spliced inline at each link's
        original position: precise inline placement would need the same
        reading-order reconstruction this module already does for words,
        applied to annotation rects too, which is real additional work
        or another parser pass. Appending is honest about that (it's a
        recovered list, not a reconstruction of where each link sat) and
        already resolves the two findings `invisible_annotations` and
        `unclickable_urls` exist to surface.
        """
        invisible = self.invisible_annotations
        if not invisible:
            return self.text
        lines = [self.text, "", "Additional links found in this document (not visible in its text):"]
        for a in invisible:
            lines.append(f"- {a.uri}")
        return "\n".join(lines)


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


_REPEATED_CHAR_RUN = re.compile(r"(.)\1{3,}")
# Detection threshold is deliberately higher (8+) than the collapse
# regex's own (4+): this is "does this look like whole-word duplicate
# rendering at all", not "collapse every run of this length". A genuine
# resume can contain a real 4-6-repeat digit run (a phone placeholder
# "555.555.5555", or -- the case that caught this on real data, not a
# hypothetical -- a real Gmail address "anumishra555555@gmail.com", six
# actual 5's) without being corrupted; R36's actual corruption duplicated
# every character ~17x, comfortably clear of any plausible legitimate run.
_LONG_REPEATED_CHAR_RUN = re.compile(r"(.)\1{7,}")


def _looks_like_duplicate_rendering(s: str) -> bool:
    """True only when MOST of the string is made of long repeated-character
    runs, not when it merely contains one. Caught by testing this module
    against a real resume, not a synthetic one: the first version of this
    function collapsed ANY run of 4+ identical characters anywhere in a
    string, which corrupted "anumishra555555@gmail.com" (a real email
    address with six genuine repeated digits) into "anumishra5@gmail.com"
    -- a different, wrong address. R36's actual corruption duplicates
    EVERY character of a word uniformly (roughly 17x each), so long runs
    account for nearly the whole string's length; an isolated legitimate
    repeat inside otherwise-normal text does not. Requiring both a longer
    minimum run (see _LONG_REPEATED_CHAR_RUN) and that such runs cover
    most of the string is what tells the two apart.
    """
    if not s:
        return False
    covered = sum(len(m.group(0)) for m in _LONG_REPEATED_CHAR_RUN.finditer(s))
    return covered / len(s) > 0.5


def _collapse_repeated_chars(s: str) -> str:
    """Found while building this: some résumés (R36's icon captions,
    checked directly) render a word as pdfplumber's OWN single word token
    with each character duplicated ~17x -- "harshibar" comes back as
    "hhhh...aaaa...rrrr...". This is real corruption in pdfplumber's word
    extraction for this PDF's specific font embedding (checked: NOT
    something this module's own column/reading-order logic introduces),
    and it leaks into the plain .text channel too (126 such runs found in
    R36's extracted text, not just this one caption) -- a genuine,
    pre-existing bug, out of scope to fix at the source here (it would
    need its own investigation into why pdfplumber's glyph clustering
    duplicates characters for this font, and changing the .text channel's
    output needs its own verification pass against every downstream
    scorer, not a two-line patch). Collapsed here ONLY for label-matching,
    where leaving "hhhh...aaaa..." as the label would wrongly report a
    real caption as an invisible/icon-only link -- and only when
    _looks_like_duplicate_rendering says this specific string is actually
    that pattern, not just "contains a repeated character somewhere".
    """
    if not _looks_like_duplicate_rendering(s):
        return s
    return _REPEATED_CHAR_RUN.sub(r"\1", s)


def _label_for_link(link: dict, page_words: list[Word]) -> str:
    """Text-layer words whose bounding box overlaps a hyperlink annotation's
    rect, in reading order left-to-right -- the visible text a viewer would
    associate with this link, if any. Empty when nothing overlaps: an icon
    or a graphic carries this link instead, invisible to any text-only
    read of the page.
    """
    overlapping = [
        w for w in page_words
        if w.x1 > link["x0"] and w.x0 < link["x1"]
        and w.bottom > link["top"] and w.top < link["bottom"]
    ]
    joined = " ".join(w.text for w in sorted(overlapping, key=lambda w: w.x0))
    return _collapse_repeated_chars(joined)


def extract_document(pdf_bytes_or_path) -> ExtractionResult:
    """Extract text from a PDF, column-aware, with parse-safety warnings.

    Three channels on the returned ExtractionResult: `.text_layer` (words
    only -- what every text-based parser, including this one's `.text`,
    has always returned), `.annotations` (link targets from /Annots, which
    the text layer never sees), and `.merged` (text layer plus whatever
    `.annotations` finds that the text layer alone would miss). See
    LinkAnnotation and ExtractionResult's docstrings for the two ATS
    findings this makes possible.
    """
    all_words: list[Word] = []
    pages: list[PageInfo] = []
    text_lines: list[str] = []
    warnings: list[str] = []
    annotations: list[LinkAnnotation] = []

    with pdfplumber.open(pdf_bytes_or_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            raw_words = page.extract_words(keep_blank_chars=False)
            words = [
                Word(text=w["text"], x0=w["x0"], x1=w["x1"], top=w["top"], bottom=w["bottom"], page=page_num)
                for w in raw_words
            ]

            # Annotations live independent of the text layer -- collect
            # them even on a page with none (an image-only page can still
            # carry a real link on top of the image).
            for link in page.hyperlinks:
                uri = link.get("uri")
                if not uri:
                    continue
                annotations.append(LinkAnnotation(
                    uri=uri, page=page_num,
                    x0=link["x0"], x1=link["x1"], top=link["top"], bottom=link["bottom"],
                    label=_label_for_link(link, words),
                ))

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
        annotations=annotations,
    )


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Drop-in replacement for services/parser.py's function of the same
    name: same signature and return type, column-aware extraction inside.
    """
    import io

    return extract_document(io.BytesIO(file_bytes)).text
