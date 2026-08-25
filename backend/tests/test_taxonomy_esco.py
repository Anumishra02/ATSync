"""Tests for Taxonomy.from_esco_csv's filter_generic_aliases guard.

Uses a small synthetic CSV fixture, not the real ~9.5MB ESCO download --
these tests must run in CI without an external data dependency (see
data/README.md for how to fetch the real file; scripts/compare_taxonomies.py
is the tool that needs it, not this suite). The synthetic rows below are
modeled directly on real ESCO rows found during the Phase 1 item 2
investigation (see Taxonomy.from_esco_csv's docstring) -- same shape, same
kind of noise, not fabricated in the abstract.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from services.skills.normalize import phrase_key
from services.skills.taxonomy import Taxonomy

_ROWS = [
    # A real noise case: "engineering" as a bare, high-frequency single
    # word wrongly aliased to a narrow, unrelated concept.
    {
        "conceptUri": "http://data.europa.eu/esco/skill/aaa",
        "preferredLabel": "packaging engineering",
        "altLabels": "engineering",
        "skillType": "knowledge",
    },
    # A genuinely out-of-domain but real ESCO entry -- noise for a resume
    # skill score, not a data error.
    {
        "conceptUri": "http://data.europa.eu/esco/skill/bbb",
        "preferredLabel": "perform dances",
        "altLabels": "dancing",
        "skillType": "skill/competence",
    },
    # Short, legitimate single-word skill names that are ALSO common
    # English words -- must survive the filter (this is the "Go vs. the
    # verb" ambiguity precedent; dropping these from the taxonomy
    # entirely would be worse than the noise being filtered out).
    {
        "conceptUri": "http://data.europa.eu/esco/skill/ccc",
        "preferredLabel": "R (computer programming)",
        "altLabels": "R",
        "skillType": "knowledge",
    },
    {
        "conceptUri": "http://data.europa.eu/esco/skill/ddd",
        "preferredLabel": "Java (computer programming)",
        "altLabels": "Java",
        "skillType": "knowledge",
    },
    # A legitimate multi-word alias -- never touched by the single-word
    # gate regardless of how generic its individual words are.
    {
        "conceptUri": "http://data.europa.eu/esco/skill/eee",
        "preferredLabel": "tutor students",
        "altLabels": "help students",
        "skillType": "skill/competence",
    },
    # A real, specific, low-frequency single-word skill name -- must
    # survive (not every single word is noise).
    {
        "conceptUri": "http://data.europa.eu/esco/skill/fff",
        "preferredLabel": "kotlin",
        "altLabels": "",
        "skillType": "knowledge",
    },
]


@pytest.fixture(scope="module")
def esco_csv_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("esco") / "skills_en.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["conceptUri", "preferredLabel", "altLabels", "skillType"])
        writer.writeheader()
        writer.writerows(_ROWS)
    return path


class TestFilterGenericAliasesOn:
    def test_generic_single_word_alias_is_dropped(self, esco_csv_path):
        tax = Taxonomy.from_esco_csv(esco_csv_path, filter_generic_aliases=True)
        assert tax.lookup(phrase_key("engineering")) is None

    def test_out_of_domain_but_generic_single_word_is_dropped(self, esco_csv_path):
        tax = Taxonomy.from_esco_csv(esco_csv_path, filter_generic_aliases=True)
        assert tax.lookup(phrase_key("dancing")) is None

    def test_short_ambiguous_language_names_survive(self, esco_csv_path):
        # The precedent this guards against: "r" (zipf ~5.35) and common
        # short tech tokens must not be silently dropped from the
        # taxonomy just because they're frequent English words too.
        tax = Taxonomy.from_esco_csv(esco_csv_path, filter_generic_aliases=True)
        assert tax.lookup(phrase_key("r")) is not None
        assert tax.lookup(phrase_key("java")) is not None

    def test_multiword_alias_is_never_touched(self, esco_csv_path):
        tax = Taxonomy.from_esco_csv(esco_csv_path, filter_generic_aliases=True)
        assert tax.lookup(phrase_key("help students")) is not None

    def test_specific_low_frequency_single_word_survives(self, esco_csv_path):
        tax = Taxonomy.from_esco_csv(esco_csv_path, filter_generic_aliases=True)
        assert tax.lookup(phrase_key("kotlin")) is not None

    def test_canonical_label_itself_can_be_filtered(self, esco_csv_path):
        # The gate applies to preferredLabel, not just altLabels -- a
        # skill whose OWN canonical name is a bare generic word would be
        # just as much noise as one aliased to it.
        rows = [{
            "conceptUri": "http://data.europa.eu/esco/skill/ggg",
            "preferredLabel": "processes",
            "altLabels": "",
            "skillType": "skill/competence",
        }]
        path = esco_csv_path.parent / "canonical_generic.csv"
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=["conceptUri", "preferredLabel", "altLabels", "skillType"])
            writer.writeheader()
            writer.writerows(rows)
        tax = Taxonomy.from_esco_csv(path, filter_generic_aliases=True)
        assert tax.lookup(phrase_key("processes")) is None
        assert len(tax) == 0


class TestFilterGenericAliasesOff:
    def test_disabling_the_filter_restores_the_noise(self, esco_csv_path):
        # filter_generic_aliases=False is what scripts/compare_taxonomies.py
        # uses to reproduce the "before" measurement -- must still work.
        tax = Taxonomy.from_esco_csv(esco_csv_path, filter_generic_aliases=False)
        assert tax.lookup(phrase_key("engineering")) is not None
        assert tax.lookup(phrase_key("dancing")) is not None
