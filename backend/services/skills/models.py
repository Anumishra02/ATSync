"""Domain models for the skill layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class MatchTier(str, Enum):
    """Which stage of the cascade produced this match.

    Kept on every match so the UI can show *why* a skill was detected, and so
    the eval harness can report per-tier precision. This is the debugging
    surface no commercial tool exposes.
    """

    EXACT = "exact"
    FUZZY = "fuzzy"
    SEMANTIC = "semantic"


@dataclass(frozen=True, slots=True)
class Skill:
    """A node in the skill taxonomy (ESCO / O*NET / seed)."""

    id: str
    canonical: str
    aliases: tuple[str, ...] = ()
    category: str = "unknown"

    # Ambiguity is a property of the *surface form*, not the skill:
    # "go" collides with ordinary English, "golang" does not. Only the forms
    # listed here require a supporting cue nearby.
    ambiguous_forms: tuple[str, ...] = ()
    context_cues: tuple[str, ...] = ()

    @property
    def surface_forms(self) -> tuple[str, ...]:
        return (self.canonical, *self.aliases)


@dataclass(frozen=True, slots=True)
class SkillMatch:
    """A detected skill occurrence, with provenance and location."""

    skill: Skill
    surface: str          # how it actually appeared in the text
    tier: MatchTier
    confidence: float     # 0..1
    char_start: int
    char_end: int

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"<{self.skill.id} '{self.surface}' "
            f"{self.tier.value} {self.confidence:.2f}>"
        )


@dataclass
class ExtractionResult:
    """All skills found in one document, deduplicated by skill id."""

    matches: list[SkillMatch] = field(default_factory=list)

    @property
    def skill_ids(self) -> set[str]:
        return {m.skill.id for m in self.matches}

    def best_per_skill(self) -> dict[str, SkillMatch]:
        """Highest-confidence match per skill (a skill can appear many times)."""
        best: dict[str, SkillMatch] = {}
        for m in self.matches:
            cur = best.get(m.skill.id)
            if cur is None or m.confidence > cur.confidence:
                best[m.skill.id] = m
        return best

    def tier_counts(self) -> dict[str, int]:
        counts = {t.value: 0 for t in MatchTier}
        for m in self.best_per_skill().values():
            counts[m.tier.value] += 1
        return counts
