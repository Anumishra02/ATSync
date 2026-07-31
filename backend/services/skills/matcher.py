"""Two-tier skill extraction cascade.

    tier 1  exact     token n-gram lookup against the taxonomy index
    tier 2  fuzzy     length-adaptive edit distance + word-frequency gate
                      (typos, minor variants)

A third tier (embedding-cosine semantic matching over resume text) was
built, measured against a pre-declared bar on evaluation/gold_semantic.json,
and cut -- see services/skills/README.md ("What I removed, and why") for
the ablation table and the reasoning. `embeddings.py` and
`evaluation/gold_semantic.json` are kept because Phase 2 (bi-encoder
retrieval over whole resume bullets, a different unit and a different
problem than per-n-gram cosine matching) will want a real encoder and a
paraphrase-labelled gold set again -- they are not wired into this matcher.

Design notes worth defending in a review:

* We iterate n-grams **longest first** and consume token spans, so
  "machine learning" wins over a bare "learning", and a phrase is never
  double-counted.
* Fuzzy uses a **length-scaled edit-distance allowance**, not a flat
  rapidfuzz ratio threshold. A flat threshold punishes short skill names and
  rewards long ones by construction: one edit in a 5-char word costs ~20
  ratio points, one edit in a 12-char word costs ~8 -- so a single global
  cutoff systematically rejected single-character typos in names like
  "kafka"/"nginx"/"redux" while accepting three-edit garbage in long ones.
  See `evaluation/gold_fuzzy.json` and `evaluation/run_fuzzy_ablation.py`
  for the graded-typo set that exposed this (the original 20-pair set was
  saturated -- recall was flat 1.000 from threshold 80 to 96, so it never
  actually tested anything).
* Real typos are not real words: `wordfreq` gates out fuzzy candidates that
  are themselves common English words ("reacts", "trust", "was", "get",
  "code") above a frequency cutoff, unless they're an exact taxonomy hit.
  `COMMON_WORDS` (taxonomy.py) stays as a cheap, dependency-free fallback,
  not the primary mechanism -- `wordfreq` is what actually scales to a
  13.9k-skill taxonomy without hand-enumerating every English word that
  happens to sit one edit from a skill name.
* Every match carries the tier that produced it, so precision can be
  measured per tier and the UI can show the user why a skill was detected.
"""

from __future__ import annotations

from rapidfuzz import process
from rapidfuzz.distance import Levenshtein
from wordfreq import zipf_frequency

from .models import ExtractionResult, MatchTier, Skill, SkillMatch
from .normalize import Token, ngram_keys, normalize, tokenize
from .taxonomy import COMMON_WORDS, Taxonomy

# Tunables. These are the knobs the ablation study sweeps.
FUZZY_WORD_FREQ_THRESHOLD = 2.0  # zipf; at/above this, treat the candidate as a real word, not a typo
FUZZY_MAX_LEN_DELTA = 3          # reject "java" ~ "javascript" (delta 6)
FUZZY_MIN_LEN = 4
MAX_NGRAM = 4
CONTEXT_WINDOW = 6          # tokens either side, for disambiguating short skills


def _max_edits_for_length(length: int) -> int:
    """Allowed edit distance, scaled to the candidate's length.

    1 edit up to 6 chars, 2 up to 12, 3 beyond. Deliberately a fixed
    breakpoint table, not a formula tuned to fit the gold set.
    """
    if length <= 6:
        return 1
    if length <= 12:
        return 2
    return 3


class SkillMatcher:
    def __init__(
        self,
        taxonomy: Taxonomy,
        *,
        fuzzy_word_freq_threshold: float = FUZZY_WORD_FREQ_THRESHOLD,
    ):
        self.taxonomy = taxonomy
        self.fuzzy_word_freq_threshold = fuzzy_word_freq_threshold
        self._keys = taxonomy.keys

    # ---- public API -----------------------------------------------------

    def extract(self, text: str) -> ExtractionResult:
        normalized = normalize(text)
        tokens = tokenize(normalized)
        consumed: set[int] = set()
        matches: list[SkillMatch] = []

        matches += self._exact_pass(tokens, consumed)
        matches += self._fuzzy_pass(tokens, consumed)

        return ExtractionResult(matches=matches)

    # ---- tier 1 ---------------------------------------------------------

    def _exact_pass(self, tokens: list[Token], consumed: set[int]) -> list[SkillMatch]:
        out: list[SkillMatch] = []
        for key, i, j in ngram_keys(tokens, MAX_NGRAM):
            if self._overlaps(i, j, consumed):
                continue
            skill = self.taxonomy.lookup(key)
            if skill is None:
                continue
            if not self._context_supports(key, tokens, i, j):
                continue
            out.append(self._build(skill, tokens, i, j, MatchTier.EXACT, 1.0))
            consumed.update(range(i, j))
        return out

    # ---- tier 2 ---------------------------------------------------------

    def _fuzzy_pass(self, tokens: list[Token], consumed: set[int]) -> list[SkillMatch]:
        out: list[SkillMatch] = []
        for key, i, j in ngram_keys(tokens, 2):
            if self._overlaps(i, j, consumed) or not self._fuzzy_candidate(key):
                continue
            max_edits = _max_edits_for_length(len(key))
            hit = process.extractOne(
                key, self._keys, scorer=Levenshtein.distance, score_cutoff=max_edits
            )
            if hit is None:
                continue
            matched_key, distance, _ = hit
            if abs(len(matched_key) - len(key)) > FUZZY_MAX_LEN_DELTA:
                continue
            skill = self.taxonomy.lookup(matched_key)
            if skill is None or not self._context_supports(matched_key, tokens, i, j):
                continue
            confidence = 0.9 * (1.0 - distance / (len(key) + 1))
            out.append(self._build(skill, tokens, i, j, MatchTier.FUZZY, confidence))
            consumed.update(range(i, j))
        return out

    def _fuzzy_candidate(self, key: str) -> bool:
        if len(key) < FUZZY_MIN_LEN:
            return False
        if key.isdigit():
            return False
        if all(part in COMMON_WORDS for part in key.split()):
            return False
        # A typo is not a recognizable English word: real skill-name typos
        # ("kuberrnetes", "postgrseql") score 0.0 in wordfreq, while the
        # near-miss English words that trip false matches ("reacts", "was",
        # "get", "code", "trust") score 3.5+. This is the general mechanism;
        # COMMON_WORDS above is just a cheap fallback for the exact matches
        # rapidfuzz didn't even need to run for.
        if all(
            zipf_frequency(part, "en") >= self.fuzzy_word_freq_threshold
            for part in key.split()
        ):
            return False
        return True

    # ---- helpers --------------------------------------------------------

    def _context_supports(self, key: str, tokens: list[Token], i: int, j: int) -> bool:
        """Gate ambiguous surface forms on a nearby supporting cue.

        "Helped the organisation go to market"  -> no cue        -> rejected
        "Built microservices in Go"             -> microservices -> accepted
        "Golang microservices"                  -> unambiguous form, no gate
        """
        cues = self.taxonomy.cues_for(key)
        if cues is None:
            return True
        lo = max(0, i - CONTEXT_WINDOW)
        hi = min(len(tokens), j + CONTEXT_WINDOW)
        window = " ".join(t.text for t in tokens[lo:i] + tokens[j:hi])
        return any(cue in window for cue in cues)

    @staticmethod
    def _overlaps(i: int, j: int, consumed: set[int]) -> bool:
        return any(idx in consumed for idx in range(i, j))

    @staticmethod
    def _build(
        skill: Skill,
        tokens: list[Token],
        i: int,
        j: int,
        tier: MatchTier,
        confidence: float,
    ) -> SkillMatch:
        start, end = tokens[i].start, tokens[j - 1].end
        surface = " ".join(t.text for t in tokens[i:j])
        return SkillMatch(
            skill=skill,
            surface=surface,
            tier=tier,
            confidence=round(min(confidence, 1.0), 4),
            char_start=start,
            char_end=end,
        )
