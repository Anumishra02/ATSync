"""Phase A follow-up: hybrid skill signal, seed + ESCO scored as SEPARATE
sub-signals rather than merged, per the exact test specified in
evaluation/backlog.md's hybrid entry:

  "curated tool/technology terms carry the rubric's construct; ESCO's
  competence statements carry coverage for fields the tool list can't
  reach... If rho stays near 0.65 while zero-match JDs drop, that's a
  clean win. If rho rides entirely on the seed layer, you've learned the
  coverage problem and the accuracy problem need different solutions --
  also a real finding."

Combined signal is a FALLBACK, not a blend: use seed's match ratio when
seed found >=1 skill in the JD; use ESCO's match ratio only when seed
found ZERO -- i.e. ESCO only ever fires on seed's coverage blind spots,
never overrides seed where seed has an opinion. This is the literal
operationalization of "coverage for fields the tool list can't reach,"
not "average the two."

ESCO threshold=0.55, per tune_esco_threshold.py's finding on the
disjoint 8-JD holdout: no threshold in [0.45, 0.75] cleanly separates
signal from noise (a structural finding, not a tuning miss -- see that
script's output), so 0.55 is a defensible middle point, not an optimum.

Run (from backend/):
    python scripts/hybrid_extractor_test.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.matching.chunking import normalize_document_text  # noqa: E402
from services.parsing.pdf_extract import extract_document  # noqa: E402
from services.skills.extractors import SeedExtractor  # noqa: E402
from services.skills.matcher import SkillMatcher  # noqa: E402
from services.skills.taxonomy import Taxonomy  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]
EVAL_DIR = BACKEND_DIR.parent / "evaluation"
SEED_PATH = BACKEND_DIR / "data" / "skills_seed.json"
LABELS_PATH = EVAL_DIR / "labels.csv"
JDS_V2_PATH = EVAL_DIR / "jds_v2.json"
RESUMES_DIR = EVAL_DIR / "step0" / "Resumes"

ESCO_THRESHOLD = 0.55


def _rho(pairs: list[tuple[float, float]]) -> tuple[float, float, int]:
    if len(pairs) < 3:
        return (float("nan"), float("nan"), len(pairs))
    hs, ms = [p[0] for p in pairs], [p[1] for p in pairs]
    rho, p = spearmanr(hs, ms)
    return (rho, p, len(pairs))


def main() -> int:
    with LABELS_PATH.open(encoding="utf-8") as f:
        labels = {r["id"]: r for r in csv.DictReader(f)}
    jds_v2 = json.loads(JDS_V2_PATH.read_text(encoding="utf-8"))
    clean_ids = sorted(
        (k for k, v in jds_v2.items() if not k.startswith("_") and v.get("source_url")),
        key=lambda r: int(r[1:]),
    )

    resume_texts: dict[str, str] = {}
    for rid in labels:
        pdf_path = RESUMES_DIR / f"{rid}.pdf"
        if pdf_path.exists():
            result = extract_document(pdf_path)
            if result.is_readable:
                resume_texts[rid] = normalize_document_text(result.text)

    jd_texts = {rid: normalize_document_text(jds_v2[rid]["text"]) for rid in clean_ids}

    print("Building seed matcher...")
    seed_ext = SeedExtractor(SkillMatcher(Taxonomy.from_seed_json(SEED_PATH)))

    print("Building ESCO embeddings once (slow, one-time)...")
    from esco_skill_extractor import SkillExtractor

    se = SkillExtractor()

    def esco_extract_batch(texts: list[str]) -> list[set[str]]:
        uri_lists = se._get_entity(texts, se._skill_ids, se._skill_embeddings, ESCO_THRESHOLD)
        return [{f"esco:{u}" for u in uris} for uris in uri_lists]

    jd_ids_ordered = list(jd_texts.keys())
    esco_jd_sets = dict(zip(jd_ids_ordered, esco_extract_batch(list(jd_texts.values())), strict=True))
    res_ids_ordered = list(resume_texts.keys())
    esco_res_sets = dict(zip(res_ids_ordered, esco_extract_batch(list(resume_texts.values())), strict=True))

    seed_jd_sets = {rid: seed_ext.extract(t) for rid, t in jd_texts.items()}
    seed_res_sets = {rid: seed_ext.extract(t) for rid, t in resume_texts.items()}

    seed_pairs, esco_pairs, fallback_pairs, esco_only_pairs = [], [], [], []
    seed_zero, fallback_used = 0, 0

    for rid in clean_ids:
        if rid not in resume_texts or rid not in labels:
            continue
        human = float(labels[rid]["skills"])

        seed_jd = seed_jd_sets[rid]
        esco_jd = esco_jd_sets[rid]

        if seed_jd:
            seed_ratio = len(seed_jd & seed_res_sets[rid]) / len(seed_jd)
            seed_pairs.append((human, seed_ratio))
        else:
            seed_zero += 1

        if esco_jd:
            esco_ratio = len(esco_jd & esco_res_sets[rid]) / len(esco_jd)
            esco_pairs.append((human, esco_ratio))

        # Fallback: seed's ratio when seed has an opinion; ESCO's ratio ONLY
        # when seed found nothing at all in this JD.
        if seed_jd:
            fallback_pairs.append((human, len(seed_jd & seed_res_sets[rid]) / len(seed_jd)))
        elif esco_jd:
            esco_ratio = len(esco_jd & esco_res_sets[rid]) / len(esco_jd)
            fallback_pairs.append((human, esco_ratio))
            esco_only_pairs.append((human, esco_ratio))  # the 20-split: ESCO's contribution in isolation
            fallback_used += 1
        # else: both empty, genuinely uncomputable, dropped -- not imputed.

    print(f"\nClean JDs: {len(clean_ids)}. Seed found zero skills in {seed_zero} of them.")
    print(f"Fallback signal used ESCO (seed=0) for {fallback_used} of those {seed_zero}.")

    print("\n=== rho(match ratio, human 'skills' label), JD-match mode, n=coverage ===")
    for label, pairs in [("seed alone (=fallback's 13-split)", seed_pairs),
                          (f"esco alone, all 33 (t={ESCO_THRESHOLD})", esco_pairs),
                          ("esco-only 20-split (seed=0 subset)", esco_only_pairs),
                          ("fallback (seed, else esco)", fallback_pairs)]:
        rho, p, n = _rho(pairs)
        print(f"  {label:36s}: n={n:3d} rho={rho:+.3f} (p={p:.3f})")

    # --- No-JD / resume-side check: has the hybrid architecture been
    # measured on resumes at all? Phase A's seed rho=0.653 (no-JD mode) was
    # seed-only, on resumes -- never through this fallback. ---
    print("\n" + "=" * 78)
    print("No-JD mode (resume-side): does the hybrid help here, or is seed's")
    print("0.653 already close to a ceiling this architecture can't raise?")
    print("=" * 78)

    seed_res_covered = [rid for rid in resume_texts if seed_res_sets[rid]]
    seed_res_zero = [rid for rid in resume_texts if not seed_res_sets[rid]]
    print(f"\nResumes: {len(resume_texts)}. Seed found zero skills in {len(seed_res_zero)} of them"
          f" ({seed_res_zero}).")

    seed_no_jd_pairs = [
        (float(labels[rid]["skills"]), len(seed_res_sets[rid])) for rid in seed_res_covered if rid in labels
    ]
    esco_fallback_only_pairs = [
        (float(labels[rid]["skills"]), len(esco_res_sets[rid])) for rid in seed_res_zero if rid in labels
    ]
    fallback_no_jd_pairs = [
        (
            float(labels[rid]["skills"]),
            len(seed_res_sets[rid]) if seed_res_sets[rid] else len(esco_res_sets[rid]),
        )
        for rid in resume_texts if rid in labels
    ]

    print("\n=== rho(raw skill count, human 'skills' label), no-JD mode ===")
    for label, pairs in [
        ("seed alone, seed-covered subset", seed_no_jd_pairs),
        ("esco alone, seed-ZERO subset only", esco_fallback_only_pairs),
        ("fallback (seed count, else esco count)", fallback_no_jd_pairs),
    ]:
        rho, p, n = _rho(pairs)
        note = "  << n this small can barely support any claim" if n < 10 else ""
        print(f"  {label:42s}: n={n:3d} rho={rho:+.3f} (p={p:.3f}){note}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
