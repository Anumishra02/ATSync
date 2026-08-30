"""Phase C1, second half of the pre-registered prediction: does relevance's
regression correlation (rho vs. human 'relevance' label) improve under the
hybrid, or stay flat? The contrast test (relevance_contrast_test.py)
answered the discrimination half (passes cleanly, 20/33, 18/33 genuinely
informative); this answers the ranking half. Different claims -- see that
script's docstring.

Reuses the same 33 clean JDs (jds_v2.json), same HybridSkillMatcher
wiring, same memoized ESCO extractor pattern. Computes each resume's
RelevanceScorer score against its OWN true JD (not the contrast test's
6-way ranking) under both a plain seed matcher and the hybrid, and
correlates each against the human 'relevance' label.

Run (from backend/):
    python scripts/relevance_regression_recheck.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from scipy.stats import linregress, spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.analysis.scorers import RelevanceScorer  # noqa: E402
from services.matching.chunking import normalize_document_text  # noqa: E402
from services.parsing.pdf_extract import extract_document  # noqa: E402
from services.skills.hybrid_matcher import ESCO_FALLBACK_THRESHOLD, HybridSkillMatcher, load_esco_label_lookup  # noqa: E402
from services.skills.matcher import SkillMatcher  # noqa: E402
from services.skills.taxonomy import Taxonomy  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]
EVAL_DIR = BACKEND_DIR.parent / "evaluation"
SEED_PATH = BACKEND_DIR / "data" / "skills_seed.json"
ESCO_CSV = BACKEND_DIR / "data" / "skills_en.csv"
LABELS_PATH = EVAL_DIR / "labels.csv"
JDS_V2_PATH = EVAL_DIR / "jds_v2.json"
RESUMES_DIR = EVAL_DIR / "step0" / "Resumes"


class _MemoizedEscoExtractor:
    def __init__(self, inner):
        self._inner = inner
        self._cache: dict[str, set[str]] = {}

    def extract(self, text: str) -> set[str]:
        if text not in self._cache:
            self._cache[text] = self._inner.extract(text)
        return self._cache[text]


def _make_esco_factory():
    cache: dict[str, object] = {}

    def factory():
        if "instance" not in cache:
            from services.skills.extractors import EscoEmbedExtractor
            print("  (building ESCO embeddings -- one-time, slow)")
            cache["instance"] = _MemoizedEscoExtractor(EscoEmbedExtractor(threshold=ESCO_FALLBACK_THRESHOLD))
        return cache["instance"]

    return factory


def _rho(pairs: list[tuple[float, float]]) -> dict:
    hs, ms = [p[0] for p in pairs], [p[1] for p in pairs]
    rho, p = spearmanr(hs, ms)
    sl = linregress(hs, ms)
    return {"n": len(pairs), "rho": rho, "p": p, "slope": sl.slope, "intercept": sl.intercept, "r2": sl.rvalue**2}


def main() -> int:
    with LABELS_PATH.open(encoding="utf-8") as f:
        labels = {r["id"]: r for r in csv.DictReader(f)}
    jds_v2 = json.loads(JDS_V2_PATH.read_text(encoding="utf-8"))
    clean_ids = sorted(
        (k for k, v in jds_v2.items() if not k.startswith("_") and v.get("source_url")),
        key=lambda r: int(r[1:]),
    )

    resume_texts: dict[str, str] = {}
    for rid in clean_ids:
        pdf_path = RESUMES_DIR / f"{rid}.pdf"
        if pdf_path.exists():
            result = extract_document(pdf_path)
            if result.is_readable:
                resume_texts[rid] = normalize_document_text(result.text)
    jd_texts = {rid: normalize_document_text(jds_v2[rid]["text"]) for rid in clean_ids}
    usable_ids = [rid for rid in clean_ids if rid in resume_texts]
    print(f"Usable: {len(usable_ids)}")

    seed_matcher = SkillMatcher(Taxonomy.from_seed_json(SEED_PATH))
    esco_labels = load_esco_label_lookup(ESCO_CSV)
    esco_factory = _make_esco_factory()
    scorer = RelevanceScorer()

    seed_pairs, hybrid_pairs = [], []
    print(f"\n{'id':5s}{'human':>7s}{'seed':>7s}{'hybrid':>8s}  fallback?")
    for rid in usable_ids:
        human = float(labels[rid]["relevance"])
        resume_text = resume_texts[rid]
        jd_text = jd_texts[rid]

        d_seed = scorer.score(resume_text, jd_text, seed_matcher)
        seed_val = d_seed.score if d_seed.score is not None else None

        hybrid = HybridSkillMatcher.for_jd(seed_matcher, esco_factory, esco_labels, jd_text)
        d_hybrid = scorer.score(resume_text, jd_text, hybrid)
        hybrid_val = d_hybrid.score if d_hybrid.score is not None else None

        if seed_val is not None:
            seed_pairs.append((human, seed_val))
        if hybrid_val is not None:
            hybrid_pairs.append((human, hybrid_val))

        print(f"{rid:5s}{human:7.1f}{'--' if seed_val is None else f'{seed_val:7.2f}'}"
              f"{'--' if hybrid_val is None else f'{hybrid_val:8.2f}'}  {'ESCO' if hybrid.use_esco else ''}")

    print("\n=== rho(RelevanceScorer score, human 'relevance' label) ===")
    for label, pairs in [("seed only", seed_pairs), ("hybrid", hybrid_pairs)]:
        r = _rho(pairs)
        print(f"  {label:12s}: n={r['n']:3d} rho={r['rho']:+.3f} (p={r['p']:.4f})  "
              f"slope={r['slope']:.3f} intercept={r['intercept']:.2f} r2={r['r2']:.3f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
