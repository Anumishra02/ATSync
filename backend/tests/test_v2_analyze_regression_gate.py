"""Regression gate for the dual-mode analysis pipeline (services.analysis
.run_analysis) that /v2/analyze wires into a live route -- Phase G,
closing backlog.md's item 1 ("make eval + CI... CI fails on coverage
regression or per-dimension gap moving past a threshold in the wrong
direction. Not rho -- too noisy at n=10/28 to gate on"). Same philosophy
as test_structure_regression_gate.py, applied to the whole pipeline
instead of one dimension: gate on coverage and mean signed gap, with real
margin above/around the measured baseline; never gate on Spearman rho,
which this project's own measurements (backlog.md's Phase C1/dual-mode
sections) have repeatedly found too unstable at this sample size to be a
contract rather than noise.

Baselines measured fresh against the 39-resume labeled corpus
(evaluation/labels.csv, evaluation/step0/Resumes/), run_analysis called
directly (not through the HTTP route -- same pipeline code, no need to
round-trip PDF bytes through TestClient's multipart encoding 39 times):

  quality mode (no JD): coverage 27/39 (69.2%), MAE 12.85, mean signed gap -2.59
  match mode (with JD): coverage 27/39 (69.2%), MAE 17.36, mean signed gap -8.74

Both modes score noticeably conservative relative to the human labels
(negative gap) and neither is near full coverage -- this gate protects
against those numbers getting WORSE, not a claim that they're good. Making
them better is real, separate calibration work (see backlog.md's items 3-5
and the deferred relevance-scaling/LLM-judge work), out of scope for a
regression gate.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from services.analysis.pipeline import run_analysis
from services.matching.chunking import normalize_document_text
from services.parsing.pdf_extract import extract_document
from services.skills.matcher import SkillMatcher
from services.skills.taxonomy import Taxonomy

SEED = Path(__file__).resolve().parents[1] / "data" / "skills_seed.json"
LABELS_PATH = Path(__file__).resolve().parents[2] / "evaluation" / "labels.csv"
JDS_PATH = Path(__file__).resolve().parents[2] / "evaluation" / "jds.json"
RESUMES_DIR = Path(__file__).resolve().parents[2] / "evaluation" / "step0" / "Resumes"

QUALITY_MAX_POINTS = 85  # 100 - relevance's 15, per Resume-Scores-39.xlsx's rubric

MIN_COVERAGE_FRACTION = 0.60  # real margin below the measured 0.692 for both modes

QUALITY_MAE_CEILING = 18.0  # measured 12.85
QUALITY_GAP_BAND = (-10.0, 5.0)  # measured -2.59

MATCH_MAE_CEILING = 24.0  # measured 17.36
MATCH_GAP_BAND = (-16.0, 3.0)  # measured -8.74


def _is_complete(dimensions) -> bool:
    return not any(d.status == "uncomputable" for d in dimensions)


def _measure():
    matcher = SkillMatcher(Taxonomy.from_seed_json(SEED))
    jds = json.loads(JDS_PATH.read_text(encoding="utf-8"))
    with LABELS_PATH.open(encoding="utf-8") as f:
        labels = list(csv.DictReader(f))

    quality_pairs: list[tuple[float, float]] = []
    match_pairs: list[tuple[float, float]] = []
    quality_complete = 0
    match_complete = 0
    match_attempted = 0
    attempted = 0

    for row in labels:
        pdf_path = RESUMES_DIR / f"{row['id']}.pdf"
        if not pdf_path.exists():
            continue
        extraction = extract_document(pdf_path)
        if not extraction.is_readable:
            continue
        attempted += 1
        text = normalize_document_text(extraction.text)

        quality = run_analysis(text, None, matcher)
        human_quality = (float(row["total"]) - float(row["relevance"])) / QUALITY_MAX_POINTS * 100
        quality_pairs.append((human_quality, quality.score))
        if _is_complete(quality.dimensions):
            quality_complete += 1

        jd_text = jds.get(row["field"])
        if jd_text:
            match_attempted += 1
            match = run_analysis(text, normalize_document_text(jd_text), matcher)
            match_pairs.append((float(row["total"]), match.score))
            if _is_complete(match.dimensions):
                match_complete += 1

    return {
        "attempted": attempted,
        "quality_pairs": quality_pairs,
        "quality_complete": quality_complete,
        "match_pairs": match_pairs,
        "match_complete": match_complete,
        "match_attempted": match_attempted,
    }


@pytest.fixture(scope="module")
def measurement():
    return _measure()


def _mae(pairs: list[tuple[float, float]]) -> float:
    return sum(abs(h - m) for h, m in pairs) / len(pairs)


def _mean_signed_gap(pairs: list[tuple[float, float]]) -> float:
    return sum(m - h for h, m in pairs) / len(pairs)


class TestQualityModeRegressionGate:
    def test_coverage_has_not_regressed(self, measurement):
        assert measurement["attempted"] > 0, "no readable labeled resumes found -- corpus itself may be missing"
        fraction = measurement["quality_complete"] / measurement["attempted"]
        assert fraction >= MIN_COVERAGE_FRACTION, (
            f"quality-mode coverage dropped to {measurement['quality_complete']}/"
            f"{measurement['attempted']} ({fraction:.1%}), below the {MIN_COVERAGE_FRACTION:.0%} gate"
        )

    def test_mean_absolute_error_has_not_regressed(self, measurement):
        mae = _mae(measurement["quality_pairs"])
        assert mae <= QUALITY_MAE_CEILING, f"quality-mode MAE {mae:.2f} exceeds the {QUALITY_MAE_CEILING} ceiling"

    def test_mean_signed_gap_direction_has_not_regressed(self, measurement):
        gap = _mean_signed_gap(measurement["quality_pairs"])
        lo, hi = QUALITY_GAP_BAND
        assert lo <= gap <= hi, (
            f"quality-mode mean signed gap {gap:.2f} outside [{lo}, {hi}] -- "
            "a shift this large means either a real defect or a deliberate "
            "calibration change; re-measure and move this band deliberately, "
            "don't just widen it to make the test pass"
        )


class TestMatchModeRegressionGate:
    def test_coverage_has_not_regressed(self, measurement):
        assert measurement["match_attempted"] > 0, "no field-matched JDs found for the labeled corpus"
        fraction = measurement["match_complete"] / measurement["match_attempted"]
        assert fraction >= MIN_COVERAGE_FRACTION, (
            f"match-mode coverage dropped to {measurement['match_complete']}/"
            f"{measurement['match_attempted']} ({fraction:.1%}), below the {MIN_COVERAGE_FRACTION:.0%} gate"
        )

    def test_mean_absolute_error_has_not_regressed(self, measurement):
        mae = _mae(measurement["match_pairs"])
        assert mae <= MATCH_MAE_CEILING, f"match-mode MAE {mae:.2f} exceeds the {MATCH_MAE_CEILING} ceiling"

    def test_mean_signed_gap_direction_has_not_regressed(self, measurement):
        gap = _mean_signed_gap(measurement["match_pairs"])
        lo, hi = MATCH_GAP_BAND
        assert lo <= gap <= hi, (
            f"match-mode mean signed gap {gap:.2f} outside [{lo}, {hi}] -- "
            "re-measure and move this band deliberately, don't just widen it"
        )
