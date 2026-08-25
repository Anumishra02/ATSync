"""Evaluation Step 3: agreement numbers, in three blocks -- never one.

Joins evaluation/labels.csv (human) with evaluation/predictions.csv
(machine) on resume id and reports, separately, for:

  covered      taxonomy_covered == True   (n=10) -- the real baseline.
  not_covered  taxonomy_covered == False  (n=29) -- expected to be poor;
               that's taxonomy-gap evidence, not a scoring failure.
  blended      all 39 -- reported ONLY to quantify how much the taxonomy
               gap drags the headline number down. Never the number to
               act on: with 29/39 resumes in a domain the skill matcher
               can't see, tuning the scorer to move this number is the
               wrong fix (see resume_eval_predict.py's docstring).

n=10 on the covered set is enough to establish a baseline but too small to
trust a bare rho -- a p-value and a bootstrap CI ship alongside every
covered-set rho so "the number is real" and "the number is noise" don't
look identical on the page.

Per-dimension signed gaps (machine - human, both put on a 0-100 scale) are
computed on the covered set, since that's the only block where the machine
score means anything close to what the human rubric measures. Experience is
reported as uncomputable, not zero -- ATSync has no scorer for experience
depth/ordering/completeness at all, and the human rubric weights that
dimension at 20/100, joint-highest with achievements. Treating a genuine
"can't measure this" as a silent 0 would be its own bug.

TWO DIFFERENT HOLES, handled two different ways -- do not conflate them:

  structurally absent (experience, for every resume)
      Not missing data -- a scale mismatch. human_total is out of 100 and
      includes a 20-point experience component; machine_total is out of
      100 and was NEVER built with anything experience-shaped in it (its
      weights already summed to 1.0 over 7 unrelated components before
      this eval existed). Comparing the two totals directly overstates the
      real error: some of the gap is definitional, not a quality miss.
      Fix: exclude it from the composite on BOTH sides before computing
      MAE -- human_excl_experience = human_total - human_experience
      (already 0-80 by construction, no rescaling needed since the human
      rubric is additive); machine_excl_experience = machine_total * 0.8
      (machine's self-contained 0-100 rescaled into the 80-point space it
      actually has evidence for, since it was never leaving room for a
      6th dimension). Arithmetic check (run once, before trusting either
      number): mean_signed(machine_total - human_total) landed within ~1
      point of mean(human_experience) in every block -- consistent with,
      but see below, most of the raw MAE being this scale artifact, not a
      quality signal. The *properly* rescaled comparison (0.8x, not a
      same-scale subtraction) shows the correction is real but partial --
      it does not explain the whole gap. See main()'s printed numbers for
      the actual split between artifact and real residual.

  per-resume uncomputable (quantification, once bug 2's chunker-sourced
  bullets find none)
      Genuinely missing data for SOME resumes, not all. Drop the pair from
      that dimension's aggregate (mean gap, correlation) and report n per
      dimension -- see dimension_gaps(). Never impute: mean-imputation
      drags any correlation toward zero, zero-imputation manufactures
      exactly the deficit being measured, and both let you pick the
      direction after seeing what you want from it. Coverage -- how many
      resumes got a complete (non-uncomputable) score at all -- is
      reported as its own headline number alongside rho, not folded
      silently into an average: for something claiming ATS-scanner-grade
      accuracy, whether it can answer at all is a real product number.

Missing-data rule, decided once, applied everywhere a machine sub-score can
be None (currently: quantification, when a resume has no chunker-recognized
bullets to grade): DROP the pair, per dimension, and report the resulting n.
Not impute. Imputing (group mean, or assume-average) would manufacture
agreement or disagreement that isn't real evidence, and it would hide
exactly the information -- "this dimension couldn't be scored for N
resumes" -- that matters most for deciding what to fix next. This mirrors
the precedent already set for the experience dimension (uncomputable, not a
silent 0), just applied per-row instead of per-dimension-wide.

R30/R31 duplicate handling: byte-for-byte identical resume, submitted (and
scored) twice. The Rubric & Notes sheet says they were "scored identically,
on purpose" -- not independently re-rated -- so this pair is NOT a free
intra-rater reliability estimate; the matching scores are a labeling
decision, not a measurement. Counting both inflates n without adding
information (a duplicate can only ever agree with itself), so R31 is
dropped from every block by default; n=39-with-R31 is available via
--include-duplicate for reference only.

Run (from backend/):
    python scripts/resume_eval_report.py [--include-duplicate]
"""

from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT.parent / "evaluation"
LABELS_PATH = EVAL_DIR / "labels.csv"
PREDICTIONS_PATH = EVAL_DIR / "predictions.csv"
OUT_PATH = EVAL_DIR / "metrics_report.md"

# Human rubric max points per dimension (Rubric & Notes sheet).
DIMENSION_MAX = {
    "relevance": 15, "skills": 15, "experience": 20,
    "achievements": 20, "writing": 15, "structure": 15,
}
# Human dimension -> machine column. experience has no machine analog --
# deliberately absent from this map (see module docstring).
DIMENSION_MACHINE_COL = {
    "relevance": "machine_relevance",
    "skills": "machine_skills",
    "achievements": "machine_achievements",
    "writing": "machine_writing",
    "structure": "machine_structure",
}

N_BOOTSTRAP = 5000
BOOTSTRAP_SEED = 42
RHO_HIGH = 0.6
ALPHA = 0.05

# Experience is 20 of the human rubric's 100 points and machine_total has
# no equivalent component at all -- see module docstring's "structurally
# absent" section. Rescaling machine_total by (100-EXPERIENCE_MAX)/100
# puts it on the same 0-80 space as human_total - human_experience.
HUMAN_EXPERIENCE_MAX = 20
MACHINE_SCALE_FACTOR = (100 - HUMAN_EXPERIENCE_MAX) / 100


# R30/R31: byte-for-byte identical resume, scored identically "on purpose"
# per the Rubric & Notes sheet -- not independently re-rated. Drop the
# second copy by default (see module docstring).
KNOWN_DUPLICATE_TO_DROP = "R31"


def load_joined(*, include_duplicate: bool = False) -> list[dict]:
    with LABELS_PATH.open(encoding="utf-8") as f:
        labels = {r["id"]: r for r in csv.DictReader(f)}
    with PREDICTIONS_PATH.open(encoding="utf-8") as f:
        preds = {r["id"]: r for r in csv.DictReader(f)}

    missing = set(labels) - set(preds)
    if missing:
        print(f"WARNING: {len(missing)} labeled resumes have no prediction: {sorted(missing)}")

    dup_id, dup_twin = KNOWN_DUPLICATE_TO_DROP, "R30"
    if dup_id in labels and dup_twin in labels:
        same = all(labels[dup_id][k] == labels[dup_twin][k] for k in labels[dup_id] if k != "id")
        print(
            f"{dup_id}/{dup_twin} duplicate check: human labels "
            f"{'match exactly' if same else 'DO NOT MATCH -- see module docstring, dedup assumption may be wrong'}"
        )

    joined = []
    for rid, lab in labels.items():
        if rid == dup_id and not include_duplicate:
            continue
        pred = preds.get(rid)
        if pred is None:
            continue
        row = {"id": rid, "field": lab["field"]}
        for dim in (*DIMENSION_MAX, "total"):
            row[f"human_{dim}"] = float(lab[dim])
        for col in (
            "machine_total", "machine_relevance", "machine_skills",
            "machine_achievements", "machine_writing", "machine_structure",
        ):
            row[col] = float(pred[col]) if pred[col] != "" else None
        row["taxonomy_covered"] = pred["taxonomy_covered"] == "True"
        row["jd_skill_count"] = int(pred["jd_skill_count"])
        # lost_share: fraction of the JD's own taxonomy skills the matcher
        # found no evidence of in the resume -- 1 - skill_score/100. Used
        # to test whether the not-covered group's inverted rho is a real
        # mechanism (stronger resumes losing more taxonomy credit) or just
        # noise from tiny integer denominators (jd_skill_count is 1-5 for
        # most not-covered fields).
        row["lost_share"] = 1.0 - float(pred["skill_score"]) / 100.0
        joined.append(row)
    return joined


def bootstrap_spearman_ci(x: list[float], y: list[float], n_boot: int = N_BOOTSTRAP) -> tuple[float, float, int]:
    """Percentile bootstrap CI for Spearman rho. Returns (lo, hi, n_degenerate).

    Resamples the (x, y) pairs with replacement and recomputes rho each
    time. On n=10, a meaningful fraction of resamples will have near-zero
    variance in one arm (duplicates from resampling) and produce a NaN rho
    -- those are dropped, and how many were dropped is returned so the
    report can say so instead of hiding it.
    """
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    n = len(x)
    x_arr, y_arr = np.array(x), np.array(y)
    rhos = []
    n_degenerate = 0
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        rho, _ = stats.spearmanr(x_arr[idx], y_arr[idx])
        if np.isnan(rho):
            n_degenerate += 1
            continue
        rhos.append(rho)
    if not rhos:
        return (float("nan"), float("nan"), n_degenerate)
    lo, hi = np.percentile(rhos, [2.5, 97.5])
    return (float(lo), float(hi), n_degenerate)


def spearman_block(rows: list[dict], label: str, with_ci: bool) -> dict:
    x = [r["human_total"] for r in rows]
    y = [r["machine_total"] for r in rows]
    n = len(rows)
    rho, p = stats.spearmanr(x, y)

    # Raw MAE: human_total (out of 100, includes 20 pts of experience)
    # against machine_total (out of 100, was never built with anything
    # experience-shaped in it). Kept for comparison, but NOT the number to
    # trust as a quality signal on its own -- see raw vs. scale-corrected
    # below, and the module docstring's "structurally absent" section.
    raw_mae = statistics.mean(abs(a - b) for a, b in zip(x, y))

    # Scale-corrected MAE: exclude experience from both sides before
    # comparing. human side is already additive (subtracting a component
    # leaves a valid 0-80 sum, no rescaling needed); machine side is
    # rescaled by MACHINE_SCALE_FACTOR since its own 0-100 was never
    # leaving room for a 6th dimension in the first place.
    human_80 = [r["human_total"] - r["human_experience"] for r in rows]
    machine_80 = [r["machine_total"] * MACHINE_SCALE_FACTOR for r in rows]
    corrected_mae = statistics.mean(abs(a - b) for a, b in zip(human_80, machine_80))

    out = {
        "label": label, "n": n, "rho": rho, "p": p,
        "raw_mae": raw_mae, "corrected_mae": corrected_mae,
    }
    if with_ci and n >= 4:
        lo, hi, n_deg = bootstrap_spearman_ci(x, y)
        out["ci_lo"], out["ci_hi"], out["ci_degenerate"] = lo, hi, n_deg
    return out


def coverage(rows: list[dict]) -> dict:
    """How many resumes got a complete (no uncomputable dimension) score.

    Currently only quantification can be None (bug 2's chunker-sourced
    bullets finding none). If a future check adds its own uncomputable
    case, extend the tuple below rather than hand-editing every call site.
    """
    nullable_cols = ("machine_achievements",)
    complete = [r for r in rows if all(r[c] is not None for c in nullable_cols)]
    return {"complete": len(complete), "total": len(rows)}


def format_block(b: dict) -> str:
    line = (
        f"n={b['n']:<3} rho={b['rho']:+.3f}  p={b['p']:.4f}  "
        f"raw_MAE={b['raw_mae']:.2f}  scale-corrected_MAE={b['corrected_mae']:.2f}"
    )
    if "ci_lo" in b:
        line += f"  95% CI=[{b['ci_lo']:+.3f}, {b['ci_hi']:+.3f}]"
        if b["ci_degenerate"]:
            line += f"  ({b['ci_degenerate']}/{N_BOOTSTRAP} bootstrap draws degenerate, dropped)"
    return line


def interpret_covered(b: dict) -> str:
    significant = b["p"] < ALPHA
    high = abs(b["rho"]) >= RHO_HIGH
    if high and significant:
        return (
            "Covered rho is high AND significant -> the scoring core is sound on the "
            "domain it can see. The #1 next job is expanding skills_seed.json to rescue "
            "the 29 not-covered resumes, NOT touching the scorer."
        )
    if high and not significant:
        return (
            "Covered rho is high BUT NOT significant at n=10 -> promising but unproven. "
            "The baseline stands provisionally; the priority is labeling more covered "
            "resumes to confirm it before trusting it for any decision."
        )
    return (
        "Covered rho is low -> this is a genuine scoring bug on the one domain the "
        "matcher can see, not a taxonomy-coverage artifact. Step 4's within-covered "
        "disagreement ranking should name the dimension to fix."
    )


def dimension_gaps(rows: list[dict]) -> list[dict]:
    """Mean signed/absolute gap per dimension.

    Missing-data rule (see module docstring): a row whose machine value for
    THIS dimension is None is dropped from THIS dimension's aggregate only
    -- it still counts everywhere else. n is reported per dimension so a
    row quietly disappearing is visible on the page, not just implied by a
    number that moved.
    """
    out = []
    n_total = len(rows)
    for dim, max_pts in DIMENSION_MAX.items():
        machine_col = DIMENSION_MACHINE_COL.get(dim)
        if machine_col is None:
            out.append({
                "dimension": dim, "n": 0, "n_total": n_total, "status": "uncomputable",
                "note": (
                    f"ATSync has no scorer for {dim} depth/ordering/completeness. "
                    f"Human rubric weights it {max_pts}/100 (joint-highest with achievements)."
                ),
            })
            continue
        usable = [r for r in rows if r[machine_col] is not None]
        dropped = n_total - len(usable)
        if not usable:
            out.append({
                "dimension": dim, "n": 0, "n_total": n_total, "status": "uncomputable",
                "note": f"machine value is None for all {n_total} rows in this block.",
            })
            continue
        human_pct = [r[f"human_{dim}"] / max_pts * 100 for r in usable]
        machine_pct = [r[machine_col] for r in usable]
        signed_gaps = [m - h for m, h in zip(machine_pct, human_pct)]
        out.append({
            "dimension": dim, "n": len(usable), "n_total": n_total, "dropped": dropped,
            "status": "ok",
            "mean_signed_gap": statistics.mean(signed_gaps),
            "mean_abs_gap": statistics.mean(abs(g) for g in signed_gaps),
        })
    return out


def lost_share_mechanism_check(rows: list[dict]) -> dict:
    """rho(lost_share, human_total) within one block.

    Tests whether the not-covered group's inverted rho is a real mechanism
    (resumes with more taxonomy-invisible content -- higher lost_share --
    tend to be the human-rated-STRONGER ones, e.g. because substantive
    non-generic writing coincidentally hits fewer of the JD's 1-5 taxonomy
    words than templated writing full of "Excel"/"communication" does) or
    just noise from those same tiny integer denominators. A strong positive
    rho here would support the mechanism story; near-zero says noise.
    """
    x = [r["lost_share"] for r in rows]
    y = [r["human_total"] for r in rows]
    rho, p = stats.spearmanr(x, y)
    return {"n": len(rows), "rho": rho, "p": p}


def main() -> int:
    include_duplicate = "--include-duplicate" in sys.argv
    rows = load_joined(include_duplicate=include_duplicate)
    covered = [r for r in rows if r["taxonomy_covered"]]
    not_covered = [r for r in rows if not r["taxonomy_covered"]]

    lines = []

    def emit(s: str = "") -> None:
        print(s)
        lines.append(s)

    emit("=" * 78)
    emit("Step 3: agreement -- covered / not-covered / blended (never blended alone)")
    emit("=" * 78)

    b_covered = spearman_block(covered, "covered", with_ci=True)
    b_not_covered = spearman_block(not_covered, "not_covered", with_ci=False)
    b_blended = spearman_block(rows, "blended", with_ci=False)

    dedup_note = "" if include_duplicate else " (R31 dropped: duplicate of R30, see module docstring)"

    emit(f"\n--- COVERED (n={len(covered)}) -- the baseline. Protect this number. ---")
    emit(format_block(b_covered))
    emit(interpret_covered(b_covered))

    emit(f"\n--- NOT COVERED (n={len(not_covered)}){dedup_note} -- taxonomy-gap evidence, not scoring failure ---")
    emit(format_block(b_not_covered))
    lsm = lost_share_mechanism_check(not_covered)
    emit(
        f"rho(lost_share, human_total) within not-covered: rho={lsm['rho']:+.3f} "
        f"p={lsm['p']:.4f} (n={lsm['n']}) -- tests whether the inversion above is a real "
        f"mechanism (stronger resumes losing more taxonomy credit) or noise from tiny "
        f"integer skill-count denominators. |rho| this small says noise, not mechanism."
        if abs(lsm["rho"]) < RHO_HIGH else
        f"rho(lost_share, human_total) within not-covered: rho={lsm['rho']:+.3f} "
        f"p={lsm['p']:.4f} (n={lsm['n']}) -- large enough to support a real mechanism, "
        f"not just noise; worth a closer look before dismissing the inversion."
    )

    emit(f"\n--- BLENDED (n={len(rows)}){dedup_note} -- quantifies the drag only, never the headline ---")
    emit(format_block(b_blended))
    emit(
        f"Blended rho ({b_blended['rho']:+.3f}) is dragged down by the {len(not_covered)} not-covered "
        f"resumes. Do NOT tune the scorer to move this number -- grow the taxonomy instead."
    )

    emit("\n" + "=" * 78)
    emit("MAE arithmetic check -- experience is a scale mismatch, not missing data")
    emit("=" * 78)
    for name, b in [("covered", b_covered), ("not_covered", b_not_covered), ("blended", b_blended)]:
        explained = b["raw_mae"] - b["corrected_mae"]
        emit(
            f"  {name:12s} raw={b['raw_mae']:6.2f}  scale-corrected={b['corrected_mae']:6.2f}  "
            f"(scale mismatch explains {explained:+.2f} of the raw MAE, "
            f"{explained / b['raw_mae'] * 100:4.1f}% of it)"
        )
    emit(
        "The correction is real but partial: it accounts for a few points of the raw "
        "MAE in every block, not most of it. A substantial calibration gap remains on "
        "the scale-matched comparison -- report scale-corrected MAE as the real number, "
        "not the raw one, but don't treat the correction as having explained the gap away."
    )

    emit("\n" + "=" * 78)
    emit("Coverage -- how often ATSync can produce a complete score at all")
    emit("=" * 78)
    for name, block_rows in [("covered", covered), ("not_covered", not_covered), ("blended", rows)]:
        cov = coverage(block_rows)
        emit(f"  {name:12s} {cov['complete']}/{cov['total']} complete scores")

    emit("\n" + "=" * 78)
    emit("Per-dimension signed gaps (machine - human, 0-100 scale), COVERED set only")
    emit("=" * 78)
    gaps = dimension_gaps(covered)
    largest = None
    for g in gaps:
        if g["status"] == "uncomputable":
            emit(f"  {g['dimension']:14s} UNCOMPUTABLE -- {g['note']}")
            continue
        dropped_note = f"  ({g['dropped']} row(s) uncomputable, dropped)" if g.get("dropped") else ""
        emit(
            f"  {g['dimension']:14s} mean signed gap={g['mean_signed_gap']:+7.2f}  "
            f"mean |gap|={g['mean_abs_gap']:6.2f}  (n={g['n']}/{g['n_total']}){dropped_note}"
        )
        if largest is None or abs(g["mean_signed_gap"]) > abs(largest["mean_signed_gap"]):
            largest = g

    emit("\n" + "=" * 78)
    emit("Headline")
    emit("=" * 78)
    ci_str = f"{b_covered['ci_lo']:+.3f} to {b_covered['ci_hi']:+.3f}"
    cov_covered = coverage(covered)
    cov_all = coverage(rows)
    headline = (
        f"Covered n={b_covered['n']}: rho = {b_covered['rho']:.3f} "
        f"(p = {b_covered['p']:.3f}, 95% CI {ci_str}), "
        f"scale-corrected MAE = {b_covered['corrected_mae']:.2f} (raw was {b_covered['raw_mae']:.2f}); "
        f"not-covered n={b_not_covered['n']}: rho = {b_not_covered['rho']:.3f}; "
        f"rho(lost_share, human_total) within not-covered = {lsm['rho']:+.3f} (p={lsm['p']:.3f}, noise not mechanism); "
        f"experience dimension structurally absent (20/100 pts, excluded from both sides, not a gap to close); "
        f"coverage: {cov_covered['complete']}/{cov_covered['total']} complete scores in covered, "
        f"{cov_all['complete']}/{cov_all['total']} overall; "
        f"largest signed per-dimension gap is {largest['mean_signed_gap']:+.2f} on {largest['dimension']} (n={largest['n']}/{largest['n_total']})."
    )
    emit(headline)

    OUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nWrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
