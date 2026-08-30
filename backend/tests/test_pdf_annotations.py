"""Tests for the three-channel parser extension (Phase D):
text_layer / annotations / merged, and the two ATS findings they enable
-- unclickable_urls (typed, not linked) and invisible_annotations
(linked, not visible as text). Construct ExtractionResult/Word/
LinkAnnotation directly rather than real PDFs for the pure-logic pieces;
real-PDF behavior is verified against the eval corpus directly (R01's
genuinely icon-only email links, R36's caption-backed links, R04/R19's
typed-not-linked contact info) -- see evaluation/backlog.md's Phase D
section for those numbers.
"""

from __future__ import annotations

from services.parsing.pdf_extract import (
    ExtractionResult,
    LinkAnnotation,
    Word,
    _collapse_repeated_chars,
    _label_for_link,
)


class TestCollapseRepeatedChars:
    def test_collapses_long_runs(self):
        # The exact corruption found on R36: pdfplumber's own word
        # extraction duplicated each character ~17x for one font-quirky
        # caption. Not something this module's logic introduces.
        assert _collapse_repeated_chars("hhhhhhhhhhhhhhhhharshibar") == "harshibar"

    def test_leaves_short_runs_alone(self):
        # "committee", "bookkeeper" etc. have genuine double letters --
        # collapsing anything under the corruption's actual run length
        # (4+) would mangle real words.
        assert _collapse_repeated_chars("committee") == "committee"
        assert _collapse_repeated_chars("bookkeeper") == "bookkeeper"

    def test_a_real_repeated_digit_run_is_not_corrupted(self):
        # Real bug, found by running this module against a real resume
        # (not synthetic data): "anumishra555555@gmail.com" has six
        # genuine repeated 5's, a real Gmail address. The first version of
        # this function collapsed ANY run of 4+ identical characters
        # anywhere in a string, which turned this into
        # "anumishra5@gmail.com" -- a different, wrong email address. The
        # fix requires runs to be both longer (8+) and cover most of the
        # string before treating it as R36-style whole-word duplication.
        assert _collapse_repeated_chars("anumishra555555@gmail.com") == "anumishra555555@gmail.com"

    def test_a_placeholder_phone_number_is_not_corrupted(self):
        assert _collapse_repeated_chars("555.555.5555") == "555.555.5555"


class TestLabelForLink:
    def test_finds_overlapping_word(self):
        link = {"x0": 10, "x1": 60, "top": 100, "bottom": 112}
        words = [Word(text="LinkedIn", x0=12, x1=55, top=101, bottom=110, page=1)]
        assert _label_for_link(link, words) == "LinkedIn"

    def test_empty_when_nothing_overlaps(self):
        link = {"x0": 10, "x1": 60, "top": 100, "bottom": 112}
        words = [Word(text="Elsewhere", x0=200, x1=250, top=300, bottom=310, page=1)]
        assert _label_for_link(link, words) == ""

    def test_joins_multiple_overlapping_words_left_to_right(self):
        link = {"x0": 0, "x1": 200, "top": 0, "bottom": 20}
        words = [
            Word(text="on", x0=50, x1=70, top=1, bottom=15, page=1),
            Word(text="GitHub", x0=0, x1=45, top=1, bottom=15, page=1),
        ]
        assert _label_for_link(link, words) == "GitHub on"


class TestInvisibleAndUnclickable:
    def _result(self, text: str, annotations: list[LinkAnnotation]) -> ExtractionResult:
        return ExtractionResult(text=text, pages=[object()], annotations=annotations)

    def test_icon_only_link_is_invisible(self):
        # R01's real case: an envelope icon linking mailto:, no caption.
        r = self._result(
            "Jay Highlander\n123 Anywhere St.\n",
            [LinkAnnotation(uri="mailto:jay@example.com", page=1, x0=0, x1=10, top=0, bottom=10, label="")],
        )
        assert len(r.invisible_annotations) == 1
        assert r.invisible_annotations[0].uri == "mailto:jay@example.com"

    def test_captioned_link_is_not_invisible_even_without_the_literal_url(self):
        # R36's real case: "500 stars on GitHub" links to a repo URL that
        # never appears character-for-character in the caption. A reader
        # (and this parser) can still see something links here -- that's
        # different from an icon with zero nearby text.
        r = self._result(
            "500 stars on GitHub\n",
            [LinkAnnotation(
                uri="https://github.com/harshibar/common-intern", page=1,
                x0=0, x1=10, top=0, bottom=10, label="500 stars on GitHub",
            )],
        )
        assert r.invisible_annotations == []

    def test_typed_url_with_no_annotation_is_unclickable(self):
        r = self._result("Contact: linkedin.com/in/yourname\n", [])
        assert "linkedin.com/in/yourname" in r.unclickable_urls

    def test_typed_url_matching_an_annotation_is_not_unclickable(self):
        r = self._result(
            "Reach me at hello@example.com\n",
            [LinkAnnotation(uri="mailto:hello@example.com", page=1, x0=0, x1=1, top=0, bottom=1, label="hello@example.com")],
        )
        assert r.unclickable_urls == []

    def test_merged_appends_invisible_links_not_present_in_text(self):
        r = self._result(
            "Jay Highlander\n",
            [LinkAnnotation(uri="mailto:jay@example.com", page=1, x0=0, x1=10, top=0, bottom=10, label="")],
        )
        assert "Jay Highlander" in r.merged
        assert "mailto:jay@example.com" in r.merged
        assert r.merged != r.text  # the whole point -- merged carries more than text_layer alone

    def test_merged_equals_text_when_nothing_is_invisible(self):
        r = self._result("Jay Highlander\n", [])
        assert r.merged == r.text
