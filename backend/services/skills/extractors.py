"""Extractor Protocol + implementations for the Phase A skill-extractor
benchmark (see evaluation/backlog.md's "Phase A" and
scripts/compare_extractors.py, which runs these against the corpus).

Every implementation returns a set of canonical skill IDs, namespaced by
source (`seed:<id>`, `esco:<uri>`, `lightcast:<id>`) rather than free text.
Namespacing means a raw string collision ("Python" from two different
sources) can't silently get treated as agreement or disagreement by
accident -- cross-source identity isn't attempted here (out of scope until
a benchmark result actually needs it); each source's ID set is compared
against the human labels independently, never against another source's ID
set directly.

Verified against each library's real output before writing the wrapper
below, not assumed from documentation:
  - esco-skill-extractor: SkillExtractor(...).get_skills([text]) ->
    List[List[str]] of ESCO skill URIs
    (http://data.europa.eu/esco/skill/<uuid>). First call per process
    builds sentence embeddings for all ~13.9k ESCO skills from scratch
    (slow, one-time per process -- no on-disk cache found outside the
    process; see compare_extractors.py's wall-clock reporting, which
    separates this from steady-state per-doc latency).
  - skillNer: SkillExtractor(nlp, SKILL_DB, PhraseMatcher).annotate(text)
    -> {"results": {"full_matches": [...], "ngram_scored": [...]}}, each
    entry carrying a "skill_id" (Lightcast/EMSI ID) and a "score". Writes
    skill_db_relax_20.json and token_dist.json into the CWD on first
    import as a side effect of the library itself, not this wrapper --
    gitignored, not something to fix here.
  - ojd-daps-skills: NOT wrapped. Pins numpy<2.0 with no prebuilt wheel for
    Python 3.13 and no C compiler available on this machine to build
    numpy from source -- confirmed by installing it in isolation, not
    inferred from the combined install failing. A --no-deps install with a
    manually-forced numpy 2.x was deliberately not attempted: the library's
    compiled/behavioral assumptions under numpy<2 are unknown, and a
    silently-degraded extractor would be worse than an absent one for a
    benchmark whose whole point is not trusting unverified output. Documented
    as an environment blocker, not a design decision -- revisit if this runs
    somewhere with a compiler, or if a later ojd-daps-skills release relaxes
    the pin.
"""

from __future__ import annotations

from typing import Protocol

from services.skills.matcher import SkillMatcher


class Extractor(Protocol):
    name: str

    def extract(self, text: str) -> set[str]: ...


class SeedExtractor:
    """Wraps the existing 92-term seed taxonomy (services/skills/matcher.py).

    The baseline every other candidate is measured against, not a new
    implementation -- reuses the exact matcher the live routes call.
    """

    name = "seed"

    def __init__(self, matcher: SkillMatcher):
        self._matcher = matcher

    def extract(self, text: str) -> set[str]:
        return {f"seed:{sid}" for sid in self._matcher.extract(text).skill_ids}


class EscoEmbedExtractor:
    """esco-skill-extractor: sentence-embedding cosine similarity against
    ESCO's ~13.9k skill descriptions (all-MiniLM-L6-v2 by default),
    threshold-gated. Distinct from services/skills/taxonomy.py's
    from_esco_csv path (services/scoring's ESCO comparison), which is exact/
    alias string matching over the same ESCO vocabulary -- this is a
    different extraction MECHANISM (embeddings vs. lexical), not a
    duplicate measurement of the same thing.
    """

    name = "esco_embed"

    def __init__(self, threshold: float = 0.6):
        from esco_skill_extractor import SkillExtractor  # local import: heavy (torch, sentence-transformers)

        self._se = SkillExtractor(skills_threshold=threshold)

    def extract(self, text: str) -> set[str]:
        [uris] = self._se.get_skills([text])
        return {f"esco:{uri}" for uri in uris}


class SkillNerExtractor:
    """skillNer: spaCy PhraseMatcher against the Lightcast/EMSI skill DB
    (SKILL_DB, ~31k skills bundled by the library, fetched on import).

    min_score filters ngram_scored's partial/low-confidence matches (e.g.
    "communication skills" scoring 0.57 on a oneToken partial match, seen
    in manual verification) -- full_matches are always kept regardless of
    score (the library doesn't attach one to them; they're its own
    highest-confidence bucket).
    """

    name = "skillner"

    def __init__(self, min_score: float = 0.5):
        import spacy
        from skillNer.general_params import SKILL_DB
        from skillNer.skill_extractor_class import SkillExtractor as _SkillNerExtractor
        from spacy.matcher import PhraseMatcher

        nlp = spacy.load("en_core_web_lg")
        self._extractor = _SkillNerExtractor(nlp, SKILL_DB, PhraseMatcher)
        self._min_score = min_score

    def extract(self, text: str) -> set[str]:
        results = self._extractor.annotate(text)["results"]
        ids: set[str] = set()
        for m in results.get("full_matches", []):
            if sid := m.get("skill_id"):
                ids.add(f"lightcast:{sid}")
        for m in results.get("ngram_scored", []):
            if m.get("score", 0) >= self._min_score and (sid := m.get("skill_id")):
                ids.add(f"lightcast:{sid}")
        return ids
