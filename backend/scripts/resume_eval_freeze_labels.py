"""Evaluation Step 1: freeze the human labels as the source of truth.

Reads the "Resume Scores" sheet out of evaluation/Resume-Scores-39.xlsx (the
hand-rated answer key) and writes it out as evaluation/labels.csv -- a plain,
diffable, git-friendly file. The xlsx stays wherever it is as the original
artifact (it also carries the "Rubric & Notes" sheet with scoring-band
definitions and duplicate/assumption notes -- see that sheet, not this
script, for the human rubric itself). labels.csv is what every downstream
script reads, and it's the file that gets committed and versioned: re-run
this after any re-rating so the diff shows exactly what changed.

Columns match the xlsx exactly: id, name, field, level, relevance, skills,
experience, achievements, writing, structure, total. Max points per
dimension (from the "Rubric & Notes" sheet): relevance 15, skills 15,
experience 20, achievements 20, writing 15, structure 15, total 100.

Run:
    python scripts/resume_eval_freeze_labels.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT.parent / "evaluation"
XLSX_PATH = EVAL_DIR / "Resume-Scores-39.xlsx"
OUT_PATH = EVAL_DIR / "labels.csv"

EXPECTED_HEADER = [
    "id", "name", "field", "level", "relevance", "skills",
    "experience", "achievements", "writing", "structure", "total",
]


def main() -> int:
    if not XLSX_PATH.exists():
        print(f"Not found: {XLSX_PATH}")
        return 1

    wb = openpyxl.load_workbook(XLSX_PATH, data_only=True)
    ws = wb["Resume Scores"]
    rows = list(ws.iter_rows(values_only=True))
    header, data_rows = rows[0], [r for r in rows[1:] if r[0]]

    header = [str(h).strip() for h in header]
    if header != EXPECTED_HEADER:
        print(f"Unexpected header: {header}\nExpected: {EXPECTED_HEADER}")
        return 1

    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in data_rows:
            writer.writerow(row)

    print(f"Wrote {len(data_rows)} labeled resumes to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
