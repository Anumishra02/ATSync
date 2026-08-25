"""Core data model for dual-mode (quality / match) resume analysis.

Why a status field, not just a score: a missing sub-score has three
genuinely different causes, and collapsing them into 0 destroys the
distinction a user (or a calibration effort) needs:

  scored          Computed a real number.
  uncomputable    Should have been evaluated, but the input didn't give
                  this scorer anything to work with (e.g. no bulleted
                  content at all for a quantification-style check). This
                  is NOT the same as "scored 0" -- a resume this check
                  structurally cannot read isn't the same as one it read
                  and found empty of achievements.
  not_applicable  This dimension doesn't apply in the current mode (the
                  canonical case: Relevance with no JD supplied).

Distinguishing these is what makes `available_points` (the sum of
max_points over dimensions that actually ran) meaningful, instead of a
score silently being computed out of 100 when only 85 points' worth of
dimensions could run at all.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Status = Literal["scored", "uncomputable", "not_applicable"]
Mode = Literal["quality", "match"]


@dataclass(frozen=True, slots=True)
class DimensionResult:
    dimension: str
    score: float | None
    max_points: float
    status: Status
    detail: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        # A None score paired with status="scored" would silently coerce to
        # 0 the moment anything downstream does arithmetic on it -- exactly
        # the failure mode this whole model exists to prevent. Enforce the
        # pairing here so it's impossible to construct a DimensionResult
        # that lies about which of the three states it's in.
        if self.status == "scored" and self.score is None:
            raise ValueError(f"{self.dimension}: status='scored' requires a non-None score")
        if self.status != "scored" and self.score is not None:
            raise ValueError(f"{self.dimension}: status={self.status!r} must carry score=None")

    def to_dict(self) -> dict:
        return {
            "dimension": self.dimension,
            "score": self.score,
            "max_points": self.max_points,
            "status": self.status,
            **({"detail": self.detail} if self.detail else {}),
        }


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    mode: Mode
    dimensions: list[DimensionResult]

    @property
    def scored(self) -> list[DimensionResult]:
        return [d for d in self.dimensions if d.status == "scored"]

    @property
    def available_points(self) -> float:
        """Sum of max_points over dimensions that actually ran (status
        'scored'). NOT the sum over every dimension the mode nominally
        includes -- an uncomputable dimension didn't run either, and its
        points shouldn't count as "available" any more than a
        not_applicable one's should.
        """
        return sum(d.max_points for d in self.scored)

    @property
    def raw_score(self) -> float:
        """Points actually earned, out of available_points -- not yet
        normalized to /100.
        """
        return sum(d.score for d in self.scored)

    @property
    def score(self) -> int:
        """Normalized to /100 for display.

        In match mode every dimension (including the always-present
        Relevance) contributes, so available_points is 100 by construction
        and this is raw_score unchanged -- no renormalization needed or
        performed, on purpose, per the mode's own definition.
        """
        if self.available_points == 0:
            return 0
        return round(100 * self.raw_score / self.available_points)

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "score": self.score,
            "available_points": round(self.available_points, 2),
            "raw_score": round(self.raw_score, 2),
            "dimensions": [d.to_dict() for d in self.dimensions],
        }
