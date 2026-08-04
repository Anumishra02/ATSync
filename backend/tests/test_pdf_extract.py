"""Tests for column-aware PDF extraction.

Word-sequence comparison, not line-for-line: two layouts sharing the same
content can legitimately wrap into a different number of lines (a narrower
column wraps sooner), so the thing actually under test is word *order*,
not where each line break falls.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from services.parsing.pdf_extract import Word, detect_columns, extract_document, reading_order

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "pdfs"
EXPECTED_WORDS = (FIXTURES / "expected_text.txt").read_text(encoding="utf-8").split()

REAL_CORPUS = Path(__file__).resolve().parents[2] / "test_corpus"
skip_without_real_corpus = pytest.mark.skipif(
    not REAL_CORPUS.exists(), reason="local-only real résumé corpus"
)


class TestSyntheticFixtures:
    """Five layouts, one shared ground truth -- see
    scripts/generate_synthetic_fixtures.py for why word order must match
    exactly across all five despite very different visual layouts.
    """

    @pytest.mark.parametrize(
        "filename",
        [
            "word_style.pdf",
            "google_docs_style.pdf",
            "latex_style.pdf",
            "canva_style.pdf",
            "two_column_template.pdf",
        ],
    )
    def test_word_order_matches_ground_truth(self, filename):
        result = extract_document(FIXTURES / filename)
        assert result.text.split() == EXPECTED_WORDS

    def test_single_column_layouts_detect_one_column(self):
        for filename in ["word_style.pdf", "google_docs_style.pdf", "latex_style.pdf"]:
            result = extract_document(FIXTURES / filename)
            assert result.column_counts == [1], filename

    def test_two_column_layouts_detect_two_columns(self):
        for filename in ["canva_style.pdf", "two_column_template.pdf"]:
            result = extract_document(FIXTURES / filename)
            assert result.column_counts == [2], filename


class TestColumnDetection:
    """Unit-level: column detection and reading order on hand-built word
    lists, independent of any PDF file.
    """

    def _word(self, text, x0, x1, top):
        return Word(text=text, x0=x0, x1=x1, top=top, bottom=top + 10, page=1)

    def test_no_words_returns_full_width_single_column(self):
        assert detect_columns([], page_width=600) == [(0.0, 600.0)]

    def test_single_column_page_is_not_split(self):
        # Realistic prose: each line's words land at different x extents,
        # so no vertical band stays empty across every line. A first draft
        # of this test fixed "hello" and "world" at the exact same two x
        # -positions on every single row -- which is geometrically a
        # two-column layout, just with different word text. The detector
        # was right to split it; the test scenario was wrong.
        import random

        rng = random.Random(0)
        words = []
        for y in range(50, 500, 20):
            x = 50.0
            for _ in range(rng.randint(4, 9)):
                width = rng.uniform(20, 60)
                words.append(self._word("w", x, x + width, top=y))
                x += width + rng.uniform(5, 15)
        assert detect_columns(words, page_width=600) == [(0.0, 600.0)]

    def test_a_narrow_gap_is_not_treated_as_a_gutter(self):
        # Natural word spacing, not a real column split.
        words = [self._word("a", 100, 110, top=100), self._word("b", 115, 125, top=100)]
        assert detect_columns(words, page_width=600) == [(0.0, 600.0)]

    def test_a_wide_consistent_gap_splits_into_two_columns(self):
        left = [self._word("L", 50, 150, top=y) for y in range(50, 500, 20)]
        right = [self._word("R", 400, 500, top=y) for y in range(50, 500, 20)]
        bounds = detect_columns(left + right, page_width=600)
        assert len(bounds) == 2
        assert bounds[0][0] == 0.0
        assert bounds[1][1] == 600.0
        # gutter center should land between the two blocks (150-400)
        assert 150 < bounds[0][1] < 400

    def test_a_full_width_line_defeats_a_column_split(self):
        # One line spanning the would-be gutter proves it isn't a real
        # column boundary, even though most other lines don't cross it.
        left = [self._word("L", 50, 150, top=y) for y in range(50, 500, 20)]
        right = [self._word("R", 400, 500, top=y) for y in range(50, 500, 20)]
        header = [self._word("HEADER", 50, 500, top=10)]
        assert detect_columns(left + right + header, page_width=600) == [(0.0, 600.0)]

    def test_lopsided_gap_near_the_edge_is_not_a_column_split(self):
        # A gap that would leave one "column" a sliver near the page edge
        # is more likely a margin or a decorative rule than a real column.
        words = [self._word("x", 40, 580, top=y) for y in range(50, 500, 20)]
        # gap right at the edge (bins 0-2 out of 200) shouldn't qualify --
        # candidates require s > 0, so this is already excluded; this test
        # documents that expectation rather than constructing a borderline
        # case that depends on exact bin math.
        assert detect_columns(words, page_width=600) == [(0.0, 600.0)]

    def test_reading_order_groups_same_top_into_one_line(self):
        words = [
            self._word("world", 100, 150, top=50),
            self._word("hello", 20, 60, top=50),
        ]
        lines = reading_order(words, [(0.0, 600.0)])
        assert len(lines) == 1
        assert [w.text for w in lines[0]] == ["hello", "world"]

    def test_reading_order_reads_column_zero_fully_before_column_one(self):
        left = [self._word("L2", 50, 100, top=100), self._word("L1", 50, 100, top=50)]
        right = [self._word("R1", 400, 450, top=50)]
        lines = reading_order(left + right, [(0.0, 300.0), (300.0, 600.0)])
        assert [line[0].text for line in lines] == ["L1", "L2", "R1"]


class TestParseSafety:
    def test_a_pdf_with_no_text_layer_warns_instead_of_silently_returning_empty(self, tmp_path):
        # Built via the fixture generator's own canvas, but with zero text
        # drawn -- exercises the "no words" path without needing a real
        # scanned file in the committed test suite.
        from reportlab.lib.pagesizes import LETTER
        from reportlab.pdfgen import canvas

        path = tmp_path / "blank.pdf"
        c = canvas.Canvas(str(path), pagesize=LETTER)
        c.showPage()
        c.save()

        result = extract_document(path)
        assert result.text == ""
        assert result.warnings
        assert "no extractable text" in result.warnings[0]


@skip_without_real_corpus
class TestRealCorpus:
    """Opportunistic checks against the real, gitignored résumé corpus --
    see test_corpus/README.md. Skipped entirely on a fresh clone / in CI.
    """

    def test_extraction_does_not_crash_on_every_file_in_the_corpus(self):
        failures = []
        for path in REAL_CORPUS.glob("*.pdf"):
            try:
                extract_document(path)
            except Exception as e:  # noqa: BLE001 -- want the file name on any failure
                failures.append(f"{path.name}: {e!r}")
        assert not failures, "\n".join(failures)

    def test_known_scanned_files_are_flagged_not_silently_empty(self):
        scanned = list(REAL_CORPUS.glob("resume *.pdf"))
        if not scanned:
            pytest.skip("scanned-batch files not present locally")
        for path in scanned:
            result = extract_document(path)
            assert result.text == ""
            assert result.warnings, f"{path.name} produced no text and no warning"
