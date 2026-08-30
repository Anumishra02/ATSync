"""Phase A: four-way skill-extractor benchmark (seed / ESCO-embedding /
skillNer / ojd-daps-skills), on the REBUILT JD corpus (jds_v2.json), not
the original jds.json compare_taxonomies.py still uses -- see that
script's own docstring on why the original corpus's independence from ESCO
doesn't carry over to the extractor question, and evaluation/backlog.md's
JD-rebuild section for why jds.json was retired as a benchmark at all. The
33-JD subset here is exactly the 38 minus the 5 with no source_url (R02,
R04, R07, R09, R18) -- committed via a fallback path, not a live posting,
so excluded from anything claiming to measure real-posting performance.

Only 3 of the 4 planned candidates run: ojd-daps-skills pins numpy<2.0,
which has no prebuilt wheel for Python 3.13 and no C compiler is available
on this machine to build it from source -- confirmed by installing it in
isolation (see services/skills/extractors.py's module docstring). Not
attempted with --no-deps + a forced numpy 2.x: an extractor whose
behavior under an unsupported numpy version is unverified is worse than an
absent one here, given the whole point is not trusting unverified output.

Threshold tuning (esco-skill-extractor's cosine cutoff) is NOT done in
this pass -- still the library default (0.6). A4 says any tuning must
happen on JDs outside this 33, which needs its own held-out JD set this
run doesn't build; left as explicit follow-up rather than rushed.

Run (from backend/, after `pip install esco-skill-extractor skillNer spacy
ipython` and `python -m spacy download en_core_web_lg` -- see
evaluation/backlog.md's Phase A section):
    python scripts/compare_extractors.py
"""

from __future__ import annotations

import csv
import json
import statistics
import sys
import time
from pathlib import Path

from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.matching.chunking import normalize_document_text  # noqa: E402
from services.parsing.pdf_extract import extract_document  # noqa: E402
from services.skills.extractors import EscoEmbedExtractor, Extractor, SeedExtractor, SkillNerExtractor  # noqa: E402
from services.skills.matcher import SkillMatcher  # noqa: E402
from services.skills.taxonomy import Taxonomy  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]
EVAL_DIR = BACKEND_DIR.parent / "evaluation"
SEED_PATH = BACKEND_DIR / "data" / "skills_seed.json"
LABELS_PATH = EVAL_DIR / "labels.csv"
JDS_V2_PATH = EVAL_DIR / "jds_v2.json"
RESUMES_DIR = EVAL_DIR / "step0" / "Resumes"

# Same field-name heuristic compare_taxonomies.py uses -- kept identical so
# the two scripts' tech/non-tech split is directly comparable, not two
# slightly different definitions of the same thing.
_TECH_FIELD_MARKERS = ("computer science", "software", "data science", "swe", "full-stack", "hci", "electrical eng")


def _is_tech_field(field: str) -> bool:
    low = field.lower()
    return any(m in low for m in _TECH_FIELD_MARKERS)


def _rho(pairs: list[tuple[float, float]]) -> tuple[float, float, int]:
    if len(pairs) < 3:
        return (float("nan"), float("nan"), len(pairs))
    hs = [p[0] for p in pairs]
    ms = [p[1] for p in pairs]
    rho, p = spearmanr(hs, ms)
    return (rho, p, len(pairs))


def load_extractors() -> dict[str, Extractor]:
    print("Loading extractors (esco_embed builds ESCO embeddings from scratch on first use -- slow, one-time)...")
    seed_matcher = SkillMatcher(Taxonomy.from_seed_json(SEED_PATH))
    out: dict[str, Extractor] = {"seed": SeedExtractor(seed_matcher)}
    try:
        out["esco_embed"] = EscoEmbedExtractor()
    except Exception as e:
        print(f"  esco_embed unavailable: {e!r}")
    try:
        out["skillner"] = SkillNerExtractor()
    except Exception as e:
        print(f"  skillner unavailable: {e!r}")
    return out


def main() -> int:
    with LABELS_PATH.open(encoding="utf-8") as f:
        labels = {r["id"]: r for r in csv.DictReader(f)}
    jds_v2 = json.loads(JDS_V2_PATH.read_text(encoding="utf-8"))
    clean_ids = sorted(
        (k for k, v in jds_v2.items() if not k.startswith("_") and v.get("source_url")),
        key=lambda r: int(r[1:]),
    )
    print(f"Clean (source_url-backed) JDs: {len(clean_ids)}/{sum(1 for k in jds_v2 if not k.startswith('_'))}")

    extractors = load_extractors()
    names = list(extractors)

    # Resume text, extracted once, reused across every extractor.
    resume_texts: dict[str, str] = {}
    for rid in labels:
        pdf_path = RESUMES_DIR / f"{rid}.pdf"
        if not pdf_path.exists():
            continue
        result = extract_document(pdf_path)
        if result.is_readable:
            resume_texts[rid] = normalize_document_text(result.text)

    jd_texts: dict[str, str] = {
        rid: normalize_document_text(jds_v2[rid]["text"]) for rid in clean_ids
    }

    # --- per-extractor extraction pass, timed ---
    jd_skills: dict[str, dict[str, set[str]]] = {n: {} for n in names}
    resume_skills: dict[str, dict[str, set[str]]] = {n: {} for n in names}
    timings: dict[str, list[float]] = {n: [] for n in names}

    for name, ext in extractors.items():
        for rid, text in jd_texts.items():
            t0 = time.perf_counter()
            jd_skills[name][rid] = ext.extract(text)
            timings[name].append(time.perf_counter() - t0)
        for rid, text in resume_texts.items():
            t0 = time.perf_counter()
            resume_skills[name][rid] = ext.extract(text)
            timings[name].append(time.perf_counter() - t0)

    print("\n=== JD coverage (JDs with >=1 skill), 33 clean JDs ===")
    for name in names:
        hits = sum(1 for rid in clean_ids if jd_skills[name][rid])
        print(f"  {name:12s}: {hits}/{len(clean_ids)} ({hits / len(clean_ids):.0%})")

    print("\n=== Resume coverage (resumes with >=1 skill), never measured before ===")
    for name in names:
        hits = sum(1 for rid in resume_texts if resume_skills[name][rid])
        print(f"  {name:12s}: {hits}/{len(resume_texts)} ({hits / len(resume_texts):.0%})")

    print("\n=== Mean skills per doc ===")
    for name in names:
        jd_counts = [len(jd_skills[name][rid]) for rid in clean_ids]
        res_counts = [len(resume_skills[name][rid]) for rid in resume_texts]
        print(
            f"  {name:12s}: JD mean={statistics.mean(jd_counts):5.1f} median={statistics.median(jd_counts):4.0f} max={max(jd_counts):3d}   "
            f"resume mean={statistics.mean(res_counts):5.1f} median={statistics.median(res_counts):4.0f} max={max(res_counts):3d}"
        )

    print("\n=== rho(raw resume skill count, human 'skills' label) -- no-JD mode, all 38 ===")
    for name in names:
        pairs = [
            (float(labels[rid]["skills"]), len(resume_skills[name][rid]))
            for rid in resume_texts if rid in labels
        ]
        rho, p, n = _rho(pairs)
        print(f"  {name:12s}: n={n:3d} rho={rho:+.3f} (p={p:.3f})")

    print("\n--- split tech / non-tech (no-JD mode) ---")
    for name in names:
        for bucket_label, pred in (("tech", _is_tech_field), ("non-tech", lambda f: not _is_tech_field(f))):
            pairs = [
                (float(labels[rid]["skills"]), len(resume_skills[name][rid]))
                for rid in resume_texts if rid in labels and pred(labels[rid]["field"])
            ]
            rho, p, n = _rho(pairs)
            print(f"  {name:12s} {bucket_label:9s}: n={n:3d} rho={rho:+.3f} (p={p:.3f})")

    print("\n=== rho(match ratio, human 'skills' label) -- JD-match mode, 33 clean ===")
    for name in names:
        pairs = []
        for rid in clean_ids:
            if rid not in resume_skills[name] or rid not in labels:
                continue
            jd_set = jd_skills[name][rid]
            if not jd_set:
                continue  # this extractor found nothing in this JD -- not a ratio, a coverage miss
            ratio = len(jd_set & resume_skills[name][rid]) / len(jd_set)
            pairs.append((float(labels[rid]["skills"]), ratio))
        rho, p, n = _rho(pairs)
        print(f"  {name:12s}: n={n:3d} rho={rho:+.3f} (p={p:.3f})")

    print("\n=== Wall-clock per doc (mean over all JD+resume calls; esco_embed's FIRST call includes one-time embedding build) ===")
    for name in names:
        t = timings[name]
        print(f"  {name:12s}: mean={statistics.mean(t)*1000:7.1f}ms  first={t[0]*1000:8.1f}ms  median={statistics.median(t)*1000:7.1f}ms  n_calls={len(t)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
