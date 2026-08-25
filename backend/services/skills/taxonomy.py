"""Skill taxonomy loading and indexing.

Two loaders share one in-memory index:

  * ``Taxonomy.from_seed_json``  - the bootstrap set checked into the repo,
    so tests and CI never depend on an external download.
  * ``Taxonomy.from_esco_csv``   - the real thing (~13.9k skills). Drop the
    ESCO ``skills_en.csv`` into ``data/`` and point the loader at it.

The index maps a *phrase key* (see normalize.phrase_key) to a Skill. Multiple
aliases collapse onto the same Skill, which is how "restful apis",
"rest api" and "restful api" all resolve to one node instead of the three
dead pool entries the v1 scorer had.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from pathlib import Path

from wordfreq import zipf_frequency

from .models import Skill
from .normalize import phrase_key

# Words that fuzzy matching must never latch onto. Without this guard,
# rapidfuzz happily maps ordinary resume prose onto skill names.
COMMON_WORDS: frozenset[str] = frozenset(
    """
    about above across after again against all also always among another any
    around because been before being below between both build built during
    each every from have here into just like made make making many more most
    much must never only other over same should since some such than that
    their them then there these they this those through under until upon
    using very were what when where which while will with within without
    work worked working team teams member members role roles year years
    month months project projects company companies client clients user users
    system systems process processes result results based across responsible
    """.split()
)

# Used only by Taxonomy.from_esco_csv's filter_generic_aliases -- see that
# method's docstring for the full investigation. Length gate comes first
# and matters most: it's what keeps "r" (zipf 5.35) and "go" (zipf 6.03),
# both real short language names, out of the frequency cutoff's reach.
_ESCO_ALIAS_ZIPF_THRESHOLD = 4.0
_ESCO_ALIAS_MIN_LEN_FOR_GATING = 5


def _is_generic_single_word(surface_form: str) -> bool:
    words = surface_form.split()
    if len(words) != 1:
        return False
    word = words[0]
    return len(word) >= _ESCO_ALIAS_MIN_LEN_FOR_GATING and zipf_frequency(word, "en") >= _ESCO_ALIAS_ZIPF_THRESHOLD


class Taxonomy:
    """An indexed collection of skills."""

    def __init__(self, skills: Iterable[Skill]):
        self._skills: dict[str, Skill] = {}
        self._index: dict[str, Skill] = {}
        # phrase key -> cues that must appear nearby for the match to count
        self._gated: dict[str, tuple[str, ...]] = {}
        for skill in skills:
            self.add(skill)

    # ---- construction ---------------------------------------------------

    def add(self, skill: Skill) -> None:
        self._skills[skill.id] = skill
        for form in skill.surface_forms:
            key = phrase_key(form)
            if not key:
                continue
            # First writer wins: canonical forms are added before aliases,
            # so a canonical never gets shadowed by another skill's alias.
            self._index.setdefault(key, skill)
        for form in skill.ambiguous_forms:
            gated_key = phrase_key(form)
            if gated_key:
                self._gated[gated_key] = skill.context_cues

    @classmethod
    def from_seed_json(cls, path: str | Path) -> Taxonomy:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            Skill(
                id=entry["id"],
                canonical=entry["canonical"],
                aliases=tuple(entry.get("aliases", [])),
                category=entry.get("category", "unknown"),
                ambiguous_forms=tuple(entry.get("ambiguous_forms", [])),
                context_cues=tuple(entry.get("context_cues", [])),
            )
            for entry in data
        )

    @classmethod
    def from_esco_csv(cls, path: str | Path, filter_generic_aliases: bool = True) -> Taxonomy:
        """Load ESCO's ``skills_en.csv`` (Phase 1 item 2, ~13.9k skills).

        Relevant columns: conceptUri, preferredLabel, altLabels (newline
        separated), skillType. We derive a stable short id from the URI tail.

        ``filter_generic_aliases`` (default True) drops a real class of
        noise found by measuring, not assuming, what a naive swap from the
        92-term seed taxonomy actually does: ESCO's ~98k surface forms
        include many single generic English words loosely aliased to a
        much narrower concept -- "engineering" -> "packaging engineering",
        "processes" -> "perform ground-handling maintenance procedures",
        "measurement" -> "metrology", plus genuinely out-of-domain entries
        ("dancing", "soccer") that are real ESCO skills but noise for a
        resume's professional-skill score. None of these are fuzzy-tier
        near-misses matcher.py's wordfreq gate already guards against --
        they land as MatchTier.EXACT, because they're indexed as literal
        surface forms. On the 39-resume eval corpus this alone dropped
        Skills' (no-JD mode) correlation with the human label from
        rho=0.653 (seed, p<0.001) to rho=0.212 (raw ESCO swap, p=0.196,
        not significant) -- a regression, not an upgrade, exactly because
        the taxonomy got 151x bigger without curation scaling with it.

        Gating on zipf_frequency alone -- the same mechanism already used
        for the fuzzy tier and for WritingScorer's repetition check --
        very nearly reintroduced the "Go the language vs. the common verb"
        ambiguity problem this project already solved once, in a worse
        form: "r" (zipf 5.35) and "go" (zipf 6.03) are both real,
        short language names that would get silently dropped from the
        taxonomy entirely (not just fuzzy-gated) by a length-blind
        frequency cutoff. Gated on length too (only single words of 5+
        characters are eligible) for exactly that reason -- short tokens
        are where legitimate acronym/language-name collisions
        concentrate, and multi-word aliases ("help students") are never
        touched by this at all, gated or not. Re-measured after both
        guards: rho=0.496 (p=0.001) -- real, significant signal restored,
        with "r"/"go"/"java"/"sql"/"python" all still resolving correctly.
        Still below the seed taxonomy's rho=0.653 -- ESCO is broader, not
        more precise, and this filter narrows the gap without claiming to
        close it. See scripts/compare_taxonomies.py for the full
        side-by-side and evaluation/backlog.md's ESCO section for the
        writeup.
        """
        skills: list[Skill] = []
        with Path(path).open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                label = (row.get("preferredLabel") or "").strip()
                if not label:
                    continue
                uri = (row.get("conceptUri") or "").rstrip("/")
                alt = (a.strip() for a in (row.get("altLabels") or "").split("\n"))
                aliases = [a for a in alt if a]
                if filter_generic_aliases:
                    if _is_generic_single_word(label):
                        continue
                    aliases = [a for a in aliases if not _is_generic_single_word(a)]
                skills.append(
                    Skill(
                        id=uri.rsplit("/", 1)[-1] or phrase_key(label),
                        canonical=label,
                        aliases=tuple(aliases),
                        category=(row.get("skillType") or "unknown").strip(),
                    )
                )
        return cls(skills)

    # ---- lookup ---------------------------------------------------------

    def lookup(self, key: str) -> Skill | None:
        return self._index.get(key)

    def cues_for(self, key: str) -> tuple[str, ...] | None:
        """Cues required for this surface form, or None if it is unambiguous."""
        return self._gated.get(key)

    def get(self, skill_id: str) -> Skill | None:
        return self._skills.get(skill_id)

    @property
    def keys(self) -> list[str]:
        """All indexed phrase keys — the candidate pool for fuzzy matching."""
        return list(self._index)

    def __len__(self) -> int:
        return len(self._skills)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Taxonomy {len(self._skills)} skills, {len(self._index)} surface forms>"
