"""HybridSkillMatcher: seed primary, ESCO fallback -- for JD-match mode only.

Drop-in replacement for `SkillMatcher` wherever one is expected
(`score_resume`, `SkillsScorer`, `RelevanceScorer` all just call
`matcher.extract(text) -> ExtractionResult`, and don't otherwise care what
produced it). No-JD mode does NOT use this -- see evaluation/backlog.md's
Phase B section: the fallback measurably *hurts* no-JD mode (0.474 vs
seed's 0.716), because a seed zero means something different on a resume
(plausibly a true "no named tools") than on a JD (almost certainly a
vocabulary failure, since the posting demonstrably contains skills).

The fallback decision is made ONCE per job description, not per call --
bound at construction via `for_jd`, using the JD's whole text. This has to
be a per-JD decision, not a per-call one: a set intersection between
"skills found in the JD" and "skills found in the resume" only means
anything if both sides were extracted with the same vocabulary. Construct
a fresh instance per JD via `for_jd`; never reuse one across JDs.

Threshold: 0.55, per tune_esco_threshold.py's finding on a held-out set
disjoint from the eval corpus -- not an optimum (none exists in the swept
range), a defensible middle point. See that script and
evaluation/backlog.md's "Threshold tuning" section.

ESCO extraction happens per JD CHUNK (not once per whole document), so it
slots into score_resume's existing per-chunk emphasis-weighting
(REQUIRED/PREFERRED/UNSPECIFIED) for free -- an ESCO match inherits the
weight of whichever chunk it was found in, exactly like a seed match does.
Known cost, not hidden: this means one embedding-similarity call per
scorable chunk when the fallback is active, not one per document (Phase
A's 359ms/doc mean was measured at whole-document granularity). Accepted
for now because match-mode scoring is a one-off user action, not a hot
path; revisit if it proves too slow in practice.

Known limitation, not hidden: ESCO matches carry char_start=0,
char_end=len(chunk_text) (the whole originating chunk), not a precise
sub-phrase offset the way seed's token-level matches do. score_resume's
evidence linking still works -- the highlighted span is just coarser
(the whole chunk that contained the match, not the exact phrase within
it) for the fallback tier specifically.
"""

from __future__ import annotations

import csv
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from .matcher import SkillMatcher
from .models import ExtractionResult, MatchTier, Skill, SkillMatch

if TYPE_CHECKING:
    # Not imported at module load: esco_skill_extractor pulls in torch and
    # sentence-transformers, and this module must stay importable (and fast
    # to import) even when the ml extras (requirements-ml.txt) aren't
    # installed -- e.g. quality-mode-only deployments, or CI. The factory
    # callable is only ever invoked when a JD actually triggers the
    # fallback; see `extract`'s lazy `self._esco is None` check.
    from .extractors import EscoEmbedExtractor

ESCO_FALLBACK_THRESHOLD = 0.55


def load_esco_label_lookup(esco_csv_path: str | Path) -> dict[str, str]:
    """conceptUri -> preferredLabel, for turning ESCO URIs into readable
    canonical names. Same source (backend/data/skills_en.csv) and same
    lookup shape as scripts/tune_esco_threshold.py's manual-inspection
    tool -- promoted here so production code and the tuning script don't
    maintain two copies of the same CSV-reading logic.
    """
    lookup: dict[str, str] = {}
    with Path(esco_csv_path).open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            lookup[row["conceptUri"]] = row["preferredLabel"]
    return lookup


class _EscoTaxonomyProxy:
    """Minimal `Taxonomy`-shaped stand-in for the ESCO fallback path.

    score_resume calls `matcher.taxonomy.get(skill_id)` to name a skill
    that was required by the JD but never found in the resume (a "missing"
    skill -- never present in `names`, which is only populated from
    resume matches). Without this, that call crashes the first time an
    ESCO-fallback JD has any missing skill at all, which is the common
    case, not an edge case -- found by reading score_resume's code before
    this shipped, not by hitting the crash first.
    """

    def __init__(self, esco_labels: dict[str, str]):
        self._labels = esco_labels

    def get(self, skill_id: str) -> Skill | None:
        uri = skill_id.removeprefix("esco:")
        label = self._labels.get(uri)
        if label is None:
            return None
        return Skill(id=skill_id, canonical=label, category="esco")


class HybridSkillMatcher:
    """See module docstring. Construct via `for_jd`, not `__init__` directly."""

    def __init__(
        self,
        seed_matcher: SkillMatcher,
        esco_extractor_factory: Callable[[], "EscoEmbedExtractor"],
        esco_labels: dict[str, str],
        *,
        use_esco: bool,
    ):
        self._seed = seed_matcher
        self._esco_factory = esco_extractor_factory
        self._esco_labels = esco_labels
        self._esco = None  # built lazily, only if use_esco and actually called
        self.use_esco = use_esco
        self.taxonomy = seed_matcher.taxonomy if not use_esco else _EscoTaxonomyProxy(esco_labels)

    @classmethod
    def for_jd(
        cls,
        seed_matcher: SkillMatcher,
        esco_extractor_factory: Callable[[], "EscoEmbedExtractor"],
        esco_labels: dict[str, str],
        jd_text: str,
    ) -> HybridSkillMatcher:
        """Decide seed vs. ESCO for this JD, from its whole text, once."""
        seed_found = bool(seed_matcher.extract(jd_text).skill_ids)
        return cls(seed_matcher, esco_extractor_factory, esco_labels, use_esco=not seed_found)

    def extract(self, text: str) -> ExtractionResult:
        if not self.use_esco:
            return self._seed.extract(text)
        if self._esco is None:
            self._esco = self._esco_factory()  # embedding build happens here, once, only when actually needed
        uris = self._esco.extract(text)
        matches = [
            SkillMatch(
                skill=Skill(id=uri, canonical=self._esco_labels.get(uri.removeprefix("esco:"), uri), category="esco"),
                surface=self._esco_labels.get(uri.removeprefix("esco:"), uri),
                tier=MatchTier.SEMANTIC,  # the cut in-house embedding tier's slot, now populated by ESCO's
                confidence=1.0,  # esco_embed's own threshold already gated this; no finer per-match score exposed
                char_start=0,
                char_end=len(text),
            )
            for uri in uris
        ]
        return ExtractionResult(matches=matches)
