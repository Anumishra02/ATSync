"""Phase 2 gold set: schema, loading, and annotator agreement.

Judgements are anchored to **text**, not chunk indices. Indices shift the
moment the chunker changes, and silently re-pointing 950 human judgements at
different bullets is the kind of error that produces a confident, wrong
number. Text anchoring makes chunker drift a loud failure instead: if a
labelled string no longer resolves to a chunk, loading raises.

Grades are ordinal, so agreement uses **weighted** kappa. Unweighted kappa
treats a 2-vs-1 disagreement as identical to 2-vs-0, which is wrong -- those
are not equally bad, and the rubric-tightening pass depends on telling them
apart.

Schema (evaluation/gold_retrieval.json):

    {
      "rubric_version": "1.0",
      "pairs": [
        {
          "id": "pair-001",
          "resume_text": "...",
          "jd_text": "...",
          "annotator": "a",
          "judgements": [
            {"requirement": "<exact requirement chunk text>",
             "evidence":    "<exact resume chunk text>",
             "grade": 2,
             "note": "optional, why -- gold for rubric examples"}
          ]
        }
      ]
    }
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from services.matching.chunking import (
    Chunk,
    chunk_job_description,
    chunk_resume,
    normalize_document_text,
)

GRADES = (0, 1, 2)


@dataclass(frozen=True, slots=True)
class Judgement:
    requirement: str
    evidence: str
    grade: int
    note: str = ""


@dataclass
class Pair:
    id: str
    resume_text: str
    jd_text: str
    judgements: list[Judgement]
    annotator: str = "a"

    @property
    def resume_chunks(self) -> list[Chunk]:
        # Judgements were labelled against normalized chunk text (matching
        # prepare_resume's contract, not raw chunk_resume(self.resume_text)
        # -- see services/matching/chunking.py's module docstring).
        return [
            c for c in chunk_resume(normalize_document_text(self.resume_text))
            if c.is_scorable
        ]

    @property
    def requirements(self) -> list[Chunk]:
        return [
            c for c in chunk_job_description(normalize_document_text(self.jd_text))
            if c.is_scorable
        ]

    def grade_lookup(self) -> dict[tuple[str, str], int]:
        return {(j.requirement, j.evidence): j.grade for j in self.judgements}

    def relevance_for(self, requirement: str, ranked_texts: list[str]) -> list[float]:
        """Graded relevance of a ranked result list. Unjudged counts as 0."""
        lookup = self.grade_lookup()
        return [float(lookup.get((requirement, t), 0)) for t in ranked_texts]

    def total_relevant(self, requirement: str, threshold: int = 1) -> int:
        return sum(
            1 for j in self.judgements
            if j.requirement == requirement and j.grade >= threshold
        )

    def validate(self) -> list[str]:
        """Check every labelled string still resolves to a chunk."""
        req_texts = {c.text for c in self.requirements}
        ev_texts = {c.text for c in self.resume_chunks}
        problems = []
        for j in self.judgements:
            if j.requirement not in req_texts:
                problems.append(f"{self.id}: requirement not found: {j.requirement[:60]!r}")
            if j.evidence not in ev_texts:
                problems.append(f"{self.id}: evidence not found: {j.evidence[:60]!r}")
            if j.grade not in GRADES:
                problems.append(f"{self.id}: grade {j.grade} outside {GRADES}")
        return problems


def load_gold(path: str | Path, *, strict: bool = True) -> list[Pair]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    pairs = [
        Pair(
            id=p["id"],
            resume_text=p["resume_text"],
            jd_text=p["jd_text"],
            annotator=p.get("annotator", "a"),
            judgements=[Judgement(**j) for j in p["judgements"]],
        )
        for p in data["pairs"]
    ]
    problems = [msg for pair in pairs for msg in pair.validate()]
    if problems and strict:
        raise ValueError(
            "Gold set no longer matches the chunker output:\n  "
            + "\n  ".join(problems[:10])
            + ("\n  ..." if len(problems) > 10 else "")
        )
    return pairs


# ---------------------------------------------------------------------------
# Annotator agreement
# ---------------------------------------------------------------------------


def weighted_kappa(a: list[int], b: list[int], weights: str = "quadratic") -> float:
    """Cohen's kappa with ordinal weighting.

    ``quadratic`` penalises a 2-vs-0 disagreement four times as hard as
    2-vs-1, which matches how the grades are meant to be read. Returns 1.0
    when both annotators are constant and identical -- degenerate, but that
    case means the sample carries no information, not perfect agreement, so
    check the label distribution before celebrating it.
    """
    if len(a) != len(b):
        raise ValueError("annotator arrays must be the same length")
    if not a:
        return 0.0

    cats = sorted(set(a) | set(b))
    n_cat = len(cats)
    if n_cat == 1:
        return 1.0
    idx = {c: i for i, c in enumerate(cats)}
    n = len(a)

    observed = [[0.0] * n_cat for _ in range(n_cat)]
    for x, y in zip(a, b, strict=True):
        observed[idx[x]][idx[y]] += 1 / n

    row = [sum(observed[i]) for i in range(n_cat)]
    col = [sum(observed[i][j] for i in range(n_cat)) for j in range(n_cat)]

    def w(i: int, j: int) -> float:
        d = abs(cats[i] - cats[j]) / (cats[-1] - cats[0])
        return d**2 if weights == "quadratic" else d

    num = sum(w(i, j) * observed[i][j] for i in range(n_cat) for j in range(n_cat))
    den = sum(w(i, j) * row[i] * col[j] for i in range(n_cat) for j in range(n_cat))
    return 1.0 if den == 0 else 1 - num / den


def agreement_report(pairs_a: list[Pair], pairs_b: list[Pair]) -> dict:
    """Align two annotators' judgements and report agreement."""
    ga = {(p.id, j.requirement, j.evidence): j.grade for p in pairs_a for j in p.judgements}
    gb = {(p.id, j.requirement, j.evidence): j.grade for p in pairs_b for j in p.judgements}
    shared = sorted(set(ga) & set(gb))
    if not shared:
        return {"n": 0, "kappa": 0.0, "exact": 0.0, "disagreements": []}

    a = [ga[k] for k in shared]
    b = [gb[k] for k in shared]
    disagreements = [
        {"pair": k[0], "requirement": k[1], "evidence": k[2], "a": ga[k], "b": gb[k]}
        for k in shared if ga[k] != gb[k]
    ]
    dist: dict[int, int] = defaultdict(int)
    for g in a + b:
        dist[g] += 1

    return {
        "n": len(shared),
        "kappa": weighted_kappa(a, b),
        "exact": sum(1 for x, y in zip(a, b, strict=True) if x == y) / len(shared),
        "label_distribution": dict(sorted(dist.items())),
        "only_a": len(set(ga) - set(gb)),
        "only_b": len(set(gb) - set(ga)),
        "disagreements": sorted(
            disagreements, key=lambda d: -abs(d["a"] - d["b"])
        ),
    }
