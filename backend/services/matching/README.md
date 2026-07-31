# Phase 2: matching resume to JD

Chunking + retrieval baseline. Two components, both built before the model
that will eventually sit on top of them exists — same discipline that killed
`services/skills`' semantic tier: declare the bar, then see if anything
clears it.

## Chunking (`chunking.py`)

Splits resume/JD text into bullets and prose, rejoining PDF line-wraps
(`_continues`), detecting headings (`_is_heading`), and — for JDs — tagging
each unit `required` / `preferred` / `boilerplate` (`classify_emphasis`), so
a missing *required* skill and a missing *preferred* one don't score the
same. Company blurbs ("we're a fast-growing startup...") are tagged
boilerplate and never scored at all.

Rule-based on purpose: inspectable, costs nothing, and gives the eval
harness a baseline a classifier has to beat before anyone adds one.

Char offsets survive every transformation, including wrap-rejoining and
mojibake repair (`ftfy.fix_text`, run before offsets are computed — see the
module docstring for what that implies about which text offsets are
relative to). That's what makes evidence-highlighting possible later: if
offsets drift, the highlight silently lies instead of failing loudly.

## Retrieval (`retrieval.py`)

`Retriever` is a `Protocol` (`index(chunks)`, `retrieve(query, k)`), so the
eval harness is model-agnostic — `DenseRetriever` / `HybridRetriever` slot
in later without touching it.

Two implementations exist, both baselines to be beaten, not the real thing:

* **`BM25Retriever`** — Okapi BM25 lexical search. In IR, BM25 routinely
  beats undertrained dense retrievers; a bi-encoder that can't clear it
  hasn't earned its place. `test_vocabulary_mismatch_is_the_known_weakness`
  is a deliberate canary: BM25 must score zero signal on a pure paraphrase
  ("orchestrating containerised workloads" vs. a bullet that says
  "Kubernetes"). If that test ever starts passing, either the gold set lost
  its paraphrase cases or something upstream started leaking lexical
  overlap — in either case, something is wrong, not improved.
* **`RandomRetriever`** — the floor. Every metric should be read against
  it: an nDCG@5 of 0.55 sounds fine until random scores 0.50 on the same
  set, which means the set is too small or too easy, not the system good.

`min_score` on `BM25Retriever.retrieve` matters more than it looks: without
it, a query sharing no terms with any chunk still returns a rank-0 hit,
scored 0.0 — indistinguishable downstream from a confident match, and it
silently poisons any aggregate built on top-1. An empty list is the honest
answer when BM25 has nothing to say.

## Metrics (`evaluation/metrics.py`)

nDCG@k, MRR, recall@k, precision@k, over **graded** relevance (2 = direct
evidence, 1 = partial, 0 = irrelevant) — binary labels throw away exactly
the "close but not quite" signal that matters in resume matching. Every
metric has a hand-computed expected value in its test, not just an
assertion that it runs: a metric that's subtly wrong is worse than no
metric, since nothing about the number looks suspicious.

## What's not here yet

* **The gold set.** 15–20 (resume, JD) pairs, each requirement labelled
  against each resume bullet on the 0/1/2 scale (~950 judgements across the
  set). This is human labelling work, not code — nothing below can produce
  real numbers without it, and no synthetic stand-in is a substitute (the
  labels are the ground truth the metrics are measured against).
* **BM25 + Random run against that gold set.** Blocked on the above.
  Publish those two rows before writing `DenseRetriever` — if BM25 lands
  near random, the gold set (or the chunking feeding it) is broken, and
  that's worth knowing before attributing flatness to a model that doesn't
  exist yet.
* **`DenseRetriever`** (bi-encoder, reusing `services/skills/embeddings.py`)
  and a cross-encoder rerank stage over the top-k pairs, aggregated by
  `Emphasis`.

Expect inter-annotator agreement (κ) to land lower here than it did on the
skill-ambiguity gold set: "is Kubernetes mentioned" is nearly objective,
"does this bullet count as evidence for 3+ years building backend services"
is a judgement call. If κ comes in below ~0.6, tighten the rubric with
worked examples and re-label rather than proceeding — nDCG computed against
noisy labels is a precise-looking number measuring nothing.
