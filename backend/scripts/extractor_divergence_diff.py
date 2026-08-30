"""Cheap, corpus-wide check before writing any Phase D parsing code:
does the current column-aware extractor (services/parsing/pdf_extract.py)
diverge from pymupdf's plain page.get_text() on any resume besides R28?

R28 was found by checking ONE resume, not a sweep -- this is the sweep.
If several diverge, the parsing layer's problem is broader than
annotations (Phase D's original scope) and the fix priority changes.

Two signals per resume, since a pure character-diff ratio alone won't
reliably surface a merged-heading-style artifact (the character content
is nearly identical -- a missing newline -- while the STRUCTURE differs):
  - line count: current parser produces fewer/more lines than pymupdf
    (a merge collapses two lines into one; a split artifact does the
    opposite)
  - text similarity ratio (difflib, on whitespace-normalized text): low
    ratio means the character content itself differs meaningfully, not
    just formatting

Run (from backend/):
    python scripts/extractor_divergence_diff.py
"""

from __future__ import annotations

import difflib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.parsing.pdf_extract import extract_document  # noqa: E402

RESUMES_DIR = Path(__file__).resolve().parents[2] / "evaluation" / "step0" / "Resumes"

LINE_COUNT_RATIO_FLAG = 0.85   # flag if current has <85% or >118% of pymupdf's line count
SIMILARITY_RATIO_FLAG = 0.90   # flag if difflib ratio (on normalized text) is below this


def _normalize_for_diff(text: str) -> str:
    # Collapse whitespace runs, strip -- comparing content, not formatting.
    return re.sub(r"\s+", " ", text).strip()


def main() -> int:
    import fitz  # pymupdf

    pdfs = sorted(RESUMES_DIR.glob("*.pdf"), key=lambda p: int(p.stem[1:]))
    print(f"{'id':5s}{'cur_lines':>10s}{'pmu_lines':>10s}{'line_ratio':>11s}{'sim_ratio':>10s}  flag")

    flagged = []
    for pdf_path in pdfs:
        rid = pdf_path.stem
        current = extract_document(pdf_path)
        if not current.is_readable:
            print(f"{rid:5s}  (unreadable to current parser -- skip, not a divergence case)")
            continue
        cur_text = current.text

        doc = fitz.open(pdf_path)
        pmu_text = "".join(page.get_text() for page in doc)

        cur_lines = [ln for ln in cur_text.splitlines() if ln.strip()]
        pmu_lines = [ln for ln in pmu_text.splitlines() if ln.strip()]
        line_ratio = len(cur_lines) / len(pmu_lines) if pmu_lines else 1.0

        sim_ratio = difflib.SequenceMatcher(
            None, _normalize_for_diff(cur_text), _normalize_for_diff(pmu_text)
        ).ratio()

        flag = line_ratio < LINE_COUNT_RATIO_FLAG or line_ratio > (1 / LINE_COUNT_RATIO_FLAG) or sim_ratio < SIMILARITY_RATIO_FLAG
        if flag:
            flagged.append((rid, line_ratio, sim_ratio))
        tag = "  <<< FLAGGED" if flag else ""
        print(f"{rid:5s}{len(cur_lines):10d}{len(pmu_lines):10d}{line_ratio:11.2f}{sim_ratio:10.3f}{tag}")

    print(f"\nFlagged: {len(flagged)}/{len(pdfs)} -- {[f[0] for f in flagged]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
