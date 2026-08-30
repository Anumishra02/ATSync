"""Regression gate for the one dimension that already works.

Per evaluation/backlog.md's item 1 and the Phase 1 plan's item 5:
"Structure -- leave it alone. It's the dimension that works. Protect it
with the regression gate." Gates on MAE, mean signed gap, and coverage --
NOT Spearman rho, per the backlog's own explicit reasoning ("too noisy at
n=10/28 to gate on -- this cycle's own bootstrap CI on covered rho spans
-0.23 to +0.96"). MAE and gap direction are stable enough to be contracts;
rho isn't, at this sample size.

Current measured baseline (39 resumes, evaluation/step0/), re-measured
after the heading-prefix-split fix (chunking.py's _split_heading_prefix --
see evaluation/backlog.md's Phase D section): MAE=2.41, mean_signed_gap
=-0.67, coverage=39/39. Reported fresh, not compared against the pre-fix
figure (2.49 / -0.74) -- both are well inside the thresholds below either
way, and this dimension's coverage was already 39/39 before the fix (R28's
uncomputable case was Experience, not Structure), so this re-measurement
confirms no regression rather than showing a fix's effect. Thresholds
below have real margin above the measured baseline -- not set to the
exact measured value, which would make this gate fail on ordinary
floating-point/model noise rather than an actual regression. If
StructureScorer's real behavior changes (taxonomy swap, heading-vocabulary
edit, anything), re-measure and move these deliberately; don't loosen them
just to make a failing test pass.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from services.analysis.scorers import StructureScorer
from services.matching.chunking import normalize_document_text
from services.parsing.pdf_extract import extract_document
from services.skills.matcher import SkillMatcher
from services.skills.taxonomy import Taxonomy

SEED = Path(__file__).resolve().parents[1] / "data" / "skills_seed.json"
LABELS_PATH = Path(__file__).resolve().parents[2] / "evaluation" / "labels.csv"
RESUMES_DIR = Path(__file__).resolve().parents[2] / "evaluation" / "step0" / "Resumes"

# Real margin above the measured baseline (2.49 / -0.74 / 39/39), not the
# baseline itself -- see the module docstring for why.
MAE_CEILING = 5.0
SIGNED_GAP_BAND = (-4.0, 4.0)
MIN_COVERAGE_FRACTION = 0.90


def _measure() -> tuple[list[tuple[str, float, float]], int, int]:
    matcher = SkillMatcher(Taxonomy.from_seed_json(SEED))
    with LABELS_PATH.open(encoding="utf-8") as f:
        labels = list(csv.DictReader(f))

    pairs: list[tuple[str, float, float]] = []
    attempted = 0
    for row in labels:
        pdf_path = RESUMES_DIR / f"{row['id']}.pdf"
        if not pdf_path.exists():
            continue
        result = extract_document(pdf_path)
        if not result.is_readable:
            continue
        attempted += 1
        text = normalize_document_text(result.text)
        d = StructureScorer().score(text, None, matcher)
        if d.status == "scored":
            pairs.append((row["id"], float(row["structure"]), d.score))

    return pairs, len(pairs), attempted


@pytest.fixture(scope="module")
def measurement() -> tuple[list[tuple[str, float, float]], int, int]:
    return _measure()


class TestStructureRegressionGate:
    def test_coverage_has_not_regressed(self, measurement):
        _, scored, attempted = measurement
        assert attempted > 0, "no readable labeled resumes found -- corpus itself may be missing"
        assert scored / attempted >= MIN_COVERAGE_FRACTION, (
            f"structure coverage dropped to {scored}/{attempted} "
            f"({scored / attempted:.1%}), below the {MIN_COVERAGE_FRACTION:.0%} gate"
        )

    def test_mean_absolute_error_has_not_regressed(self, measurement):
        pairs, _, _ = measurement
        mae = sum(abs(m - h) for _, h, m in pairs) / len(pairs)
        assert mae <= MAE_CEILING, f"structure MAE {mae:.2f} exceeds the {MAE_CEILING} ceiling"

    def test_mean_signed_gap_direction_has_not_regressed(self, measurement):
        pairs, _, _ = measurement
        gap = sum(m - h for _, h, m in pairs) / len(pairs)
        lo, hi = SIGNED_GAP_BAND
        assert lo <= gap <= hi, (
            f"structure mean signed gap {gap:.2f} outside the [{lo}, {hi}] band -- "
            "a shift this large means either a real defect or the taxonomy/vocabulary "
            "underneath check_sections changed; re-measure deliberately, don't just widen the band"
        )
