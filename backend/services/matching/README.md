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

Char offsets survive every transformation, including wrap-rejoining. That's
what makes evidence-highlighting possible later: if offsets drift, the
highlight silently lies instead of failing loudly.

**Normalization is a separate, explicit step, not something chunking does
for you.** `normalize_document_text` (`ftfy.fix_text`) repairs mojibake — a
UTF-8 bullet mis-decoded as cp1252 becomes 3 characters instead of 1,
common on PDFs exported from Word on Windows — but fixing it changes the
string's length, so offsets are only valid against the *normalized* text.
Baking that into `chunk_document` would make it silently safe to call once
and silently wrong the moment anything else (rendering, a second pipeline
pass) touches the same document without normalizing identically — raw text
and chunk offsets would quietly disagree about what "the document" even is.
So: `chunk_document` / `chunk_resume` / `chunk_job_description` *require*
already-normalized input and don't touch it themselves
(`test_mojibake_bullet_is_not_recognized_without_normalizing_first` proves
that's a real precondition, not just a comment). `prepare_resume` /
`prepare_job_description` are the entry point real callers should use —
they normalize once and return a `ChunkedDocument` bundling
`canonical_text` with its `chunks`, so a caller physically cannot end up
with offsets and no matching text to slice them against. When this is
wired into an API route, `canonical_text` is what the frontend highlights
into — never whatever raw bytes a PDF extractor originally produced.

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

## Gold-set harness (`evaluation/gold.py`, `evaluation/run_retrieval_eval.py`)

Built and tested, ahead of the labelled data it will eventually score:

* **Judgements anchor to chunk *text*, not chunk index.** Indices shift the
  moment the chunker changes; silently re-pointing hundreds of human
  judgements at different bullets produces a confident, wrong number rather
  than an obvious failure. `load_gold(strict=True)` raises if any labelled
  string no longer resolves to a chunk — `test_chunker_drift_is_a_loud_failure`
  proves it.
* **Agreement is quadratic-weighted Cohen's κ**, not plain kappa: grades are
  ordinal (0/1/2), so a 2-vs-0 disagreement should cost more than 2-vs-1,
  and unweighted kappa can't express that distinction — which is exactly the
  distinction the rubric-tightening pass depends on. The degenerate case is
  handled explicitly: both annotators picking the same constant grade
  everywhere returns κ=1.0, which is "no information," not "perfect
  agreement" — the label distribution is printed alongside specifically so
  that's checkable rather than silently trusted.
* **`gold_retrieval_example.json`** is one fully-labelled (resume, JD) pair —
  4 requirements × 7 scorable bullets, every judgement carries a note
  explaining the grade. This is the worked example a human annotator should
  read (and a first pair should be labelled *together, out loud*) before
  labelling anything alone — not test fixture filler.

Run against the example pair, for real:

```
pairs 1   requirements (queries) 4   k=5
  NOTE: this is a pilot-sized set. Treat the numbers as a
  smoke test of the harness, not as a result.

system                nDCG@5     MRR   recall@5   prec@5   empty
Random (floor)         0.439   0.333      0.542    0.200   0.000
BM25                   0.750   0.750      0.583    0.150   0.000

BM25 lift over random: +0.311
```

Read the **random row**, not the BM25 row: 0.439 from pure chance, because
with only 7 bullets in the corpus and k=5, random retrieval returns 5/7 of
everything and can hardly miss. **`recall@5` is close to meaningless at
resume-sized corpora** — `nDCG@3` or `nDCG@1` (or precision at the very
top) is the metric actually worth reading until there's a reason to expect
larger resumes. This is one pilot pair; treat the numbers themselves as a
harness smoke test, not a result — see below.

## What's not here yet

* **The real gold set.** *Pilot first, not all at once*: label 5 pairs
  (4 requirements × ~7 bullets ≈ 28 judgements/pair ≈ 140 total — an
  evening, not a week), compute κ between two annotators, resolve every
  disagreement, and rewrite the rubric using the disagreements as worked
  examples. Only then scale to 15–20 pairs (~950 judgements total).
  Discovering the rubric was ambiguous after 950 judgements means
  re-labelling 950; after 140 it costs an hour. This is human labelling
  work, not code — nothing here can produce a real result without it, and
  no synthetic stand-in is a substitute, since the labels *are* the ground
  truth everything else is measured against.
* **BM25 + Random run against the real pilot set**, published, before
  `DenseRetriever` gets written — if BM25 lands near random on real data,
  the gold set or the chunking feeding it is broken, and that's worth
  knowing before attributing flatness to a model that doesn't exist yet.
* **`DenseRetriever`** (bi-encoder, reusing `services/skills/embeddings.py`)
  and a cross-encoder rerank stage over the top-k pairs, aggregated by
  `Emphasis`.

Expect κ to land lower here than it did on the skill-ambiguity gold set:
"is Kubernetes mentioned" is nearly objective; "does *migrated the
datastore to PostgreSQL* count as evidence for *3+ years building backend
services*" is a genuine judgement call, and the first pilot round should be
expected to disagree a lot — that's information, not failure. If κ comes in
below ~0.6, tighten the rubric with the disagreements as worked examples
and re-label rather than proceeding — nDCG computed against noisy labels is
a precise-looking number measuring nothing. Run
`python evaluation/run_retrieval_eval.py --agreement a.json b.json` once
two annotators' files exist — it prints κ, the label distribution, and the
worst disagreements first, and refuses to let the run proceed quietly when
κ is under 0.60.
