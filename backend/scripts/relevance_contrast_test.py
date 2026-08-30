"""Phase C1: contrast test for RelevanceScorer (services/analysis/scorers.py,
which wraps score_resume -- the current build; NOT legacy_ats_score's
keyword_score, which some of the historical 0.089-0.232 correlation
figures were measured against. This result belongs to score_resume.

Pre-registered before running (evaluation/backlog.md carries the same
text, written before this script's output was seen):

  Criterion: per-resume win rate. For each of the 33 clean-JD resumes,
  score its own true JD plus 5 randomly-drawn JDs from the other 32 (fixed
  seed, without replacement) -- 6 candidates total. Win = the true JD's
  score is the max (ties count as a win) among all 6.

  Null: no real matching signal -> true JD ranks #1 of 6 by chance = 1/6,
  expected 5.5/33 wins.

  Pass: binomial test, one-tailed, alpha=0.05, against p0=1/6. Critical
  value computed before running: >=10/33 wins (P(X>=10)=0.038).

  Prediction: relevance may pass this test (discriminate matched from
  random cleanly) while still correlating weakly with human labels in the
  regression sense -- different claims, binary separation vs. fine-grained
  ranking. If that's what's found, the proxy isn't broken; the flat
  regression is range restriction, not evidence the mechanism needs
  rewriting.

RE-RUN (Phase B): now against HybridSkillMatcher (services/skills/
hybrid_matcher.py) instead of the plain seed matcher. The first run found
that score_resume returns a structural 0 for the 20/33 seed-zero-skill
JDs, contaminating 26/33 of the original "wins" with a coverage lottery
(see evaluation/backlog.md's Phase C1 section for the full first-run
split: 7/33 genuinely computable, 5/7 win there). With the hybrid, far
more than 7/33 should now get a genuine, nonzero-or-honestly-uncomputable
score. Per the pre-registered discipline: same criterion, same threshold,
same random seed -- not renegotiated after seeing this run's number
either.

Run (from backend/):
    python scripts/relevance_contrast_test.py
"""

from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

from scipy.stats import binomtest

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

RANDOM_SEED = 20260830  # fixed, pre-registered before results were seen -- unchanged from the first run
N_RANDOM = 5
NULL_P = 1 / 6
CRITICAL_WINS = 10  # computed before running -- see module docstring


class _MemoizedEscoExtractor:
    """Wraps EscoEmbedExtractor with a text->result cache, scoped to this
    script's run. Each of the 33 JDs gets reused as a random competitor
    ~5x on average (33 draws of 5 from a pool of 32 ~ 33*5/32), and
    score_resume re-derives weights fresh per call (by design -- it
    doesn't cache), so without this the same JD/resume chunk text gets
    re-embedded repeatedly. Bounded by this run's ~33*6 candidate texts;
    not something to promote into the production class, whose caller
    (a live request) touches each text once.
    """

    def __init__(self, inner):
        self._inner = inner
        self._cache: dict[str, set[str]] = {}

    def extract(self, text: str) -> set[str]:
        if text not in self._cache:
            self._cache[text] = self._inner.extract(text)
        return self._cache[text]


def _make_esco_factory():
    """Memoized: the real embedding build (~minutes, one-time) must happen
    at most once across this entire run, no matter how many of the 33 JDs
    trigger the fallback -- NOT once per JD, which would rebuild it ~20x.
    """
    cache: dict[str, object] = {}

    def factory():
        if "instance" not in cache:
            from services.skills.extractors import EscoEmbedExtractor
            print("  (building ESCO embeddings -- one-time, slow)")
            cache["instance"] = _MemoizedEscoExtractor(EscoEmbedExtractor(threshold=ESCO_FALLBACK_THRESHOLD))
        return cache["instance"]

    return factory


def main() -> int:
    with LABELS_PATH.open(encoding="utf-8") as f:
        labels = {r["id"]: r for r in csv.DictReader(f)}
    jds_v2 = json.loads(JDS_V2_PATH.read_text(encoding="utf-8"))
    clean_ids = sorted(
        (k for k, v in jds_v2.items() if not k.startswith("_") and v.get("source_url")),
        key=lambda r: int(r[1:]),
    )
    print(f"Clean-JD resumes: {len(clean_ids)}")

    resume_texts: dict[str, str] = {}
    for rid in clean_ids:
        pdf_path = RESUMES_DIR / f"{rid}.pdf"
        if pdf_path.exists():
            result = extract_document(pdf_path)
            if result.is_readable:
                resume_texts[rid] = normalize_document_text(result.text)
    jd_texts = {rid: normalize_document_text(jds_v2[rid]["text"]) for rid in clean_ids}

    usable_ids = [rid for rid in clean_ids if rid in resume_texts]
    print(f"Usable (readable resume + clean JD): {len(usable_ids)}")

    seed_matcher = SkillMatcher(Taxonomy.from_seed_json(SEED_PATH))
    esco_labels = load_esco_label_lookup(ESCO_CSV)
    esco_factory = _make_esco_factory()
    scorer = RelevanceScorer()
    rng = random.Random(RANDOM_SEED)

    fallback_count = 0
    wins = 0
    rows = []
    for rid in usable_ids:
        resume_text = resume_texts[rid]
        pool = [other for other in usable_ids if other != rid]
        random_ids = rng.sample(pool, N_RANDOM)

        candidates = [rid] + random_ids
        scores = {}
        for cid in candidates:
            jd_text = jd_texts[cid]
            matcher = HybridSkillMatcher.for_jd(seed_matcher, esco_factory, esco_labels, jd_text)
            if matcher.use_esco:
                fallback_count += 1
            d = scorer.score(resume_text, jd_text, matcher)
            scores[cid] = d.score if d.score is not None else float("-inf")

        true_score = scores[rid]
        is_win = true_score >= max(scores.values())
        rank = 1 + sum(1 for s in scores.values() if s > true_score)
        wins += int(is_win)
        rows.append((rid, true_score, rank, is_win, random_ids))
        print(f"  {rid:5s} true_score={true_score:5.2f}  rank={rank}/6  win={'YES' if is_win else 'no '}  vs {random_ids}")

    n = len(usable_ids)
    print(f"\nESCO fallback triggered on {fallback_count}/{n * (N_RANDOM + 1)} candidate scorings.")
    print(f"\n=== Contrast test result ===")
    print(f"Wins: {wins}/{n}  (expected under null: {n * NULL_P:.1f})")
    print(f"Pre-registered pass threshold: >={CRITICAL_WINS}/{n}")

    result = binomtest(wins, n, NULL_P, alternative="greater")
    print(f"Binomial test (one-tailed, p0={NULL_P:.4f}): p={result.pvalue:.4f}")
    verdict = "PASS" if wins >= CRITICAL_WINS else "FAIL"
    print(f"Verdict: {verdict} (pre-registered criterion, not adjusted post hoc)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
