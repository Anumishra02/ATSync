# Skill extraction

Replaces v1's `SKILLS_POOL` + `if skill in text` substring check.

## Why the rewrite

v1 matched raw substrings, which produced silent false positives that
inflated every user's ATS score:

| Input | v1 extracted | Wrong because |
|---|---|---|
| `JavaScript developer` | `javascript`, **`java`** | `java` ⊂ `javascript` |
| `comfortable with loops` | **`oop`** | `oop` ⊂ `loops` |
| `GitHub Actions` | **`git`** | `git` ⊂ `github` |
| `PostgreSQL` | **`sql`** | `sql` ⊂ `postgresql` |
| `Tailwind CSS` | `tailwind`, **`css`** | shorter gram double-counted |

Three of `SKILLS_POOL`'s entries were also unreachable: `normalize()`
rewrote `"restful api" → "rest api"` *before* matching, so the pool entries
`restful api`, `restful apis` and `object-oriented programming` could never
fire.

## Design

```
text ──▶ normalize ──▶ tokenize ──▶ n-grams (longest first)
                                       │
                          ┌────────────┴────────────┐
                          ▼                          ▼
                    tier 1 exact               tier 2 fuzzy
                    taxonomy index      length-adaptive edit distance
                    conf 1.00              + word-frequency gate
                          └────────────┬────────────┘
                                       ▼
                        span-consuming greedy resolution
```

Two tiers, not three. A third (embedding-cosine semantic matching) was
built, measured against a pre-declared bar, and cut — see "What I removed,
and why" below. That's not a footnote; it's as much a part of this module's
story as what shipped.

Decisions worth defending:

* **Tokens, never substrings.** Every comparison happens on whitespace- and
  punctuation-aware tokens. `+`, `#`, `.`, `/` and `-` survive tokenization
  so `c++`, `c#`, `node.js` and `ci/cd` stay intact.
* **Longest n-gram wins, spans are consumed.** `machine learning` beats a
  bare `learning`; nothing is double-counted.
* **Fuzzy uses a length-scaled edit-distance allowance, not a flat ratio
  threshold.** See "Fuzzy tier" below — a single global cutoff punishes
  short skill names and rewards long ones by construction.
* **Ambiguity is a property of the surface form, not the skill.** `go`
  requires a supporting cue within ±6 tokens; `golang` does not. Same for
  `Excel` (verb), `Spark`, `Rust`, and `Java` (the beverage sense — found by
  the adversarial semantic gold set, not by reading the code).
* **Every match carries its tier.** Enables per-tier precision in the eval
  harness, and lets the UI show the user *why* a skill was detected —
  something no commercial tool exposes.

## Results

20 hand-labeled snippets, restricted to v1's 44-skill vocabulary so we are
measuring *matching quality*, not vocabulary size:

| System | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| v1 substring | 27 | 5 | 0 | 0.844 | 1.000 | 0.915 |
| v2 cascade | 27 | **0** | 0 | **1.000** | 1.000 | **1.000** |

v2 on its own full taxonomy (no vocabulary restriction): P 0.980 / R 1.000 / F1 0.990.

> 20 snippets is a smoke test, not a benchmark. It establishes the table
> shape. It's also too small and too easy to evaluate tiers 2 or 3 in any
> depth — see the graded, adversarial sets below for that.

## Loading the real taxonomy

The seed set is checked in so tests never need a download. For production,
grab ESCO `skills_en.csv` (~13.9k skills, CC BY 4.0):

```python
taxonomy = Taxonomy.from_esco_csv("data/esco/skills_en.csv")
```

## Fuzzy tier: length-adaptive edit distance + word-frequency gate

The original approach was `rapidfuzz.fuzz.ratio` against one flat threshold
(88.0). It looked fine on the 20-pair set — recall stayed 1.000 from
threshold 80 to 96 — which was the problem: a set that flat isn't measuring
anything. `evaluation/gold_fuzzy.json` (44 graded typos at edit distance
1/2/3, plus 15 hard negatives — real English words that sit one edit from a
skill name: `was`/aws, `get`/git, `code`/node, `reacts`/react, `trust`/rust)
exposed two real problems with the ratio approach:

**A flat ratio threshold is the wrong shape.** One edit in a 5-character
word ("kafka" → "akfka") costs about 20 ratio points; one edit in a
12-character word ("elasticsearch" → "elastcisearch") costs about 8. So one
global cutoff systematically rejects single typos in short names while
accepting three-edit garbage in long names — visible directly in the sweep
(`scripts/threshold_ablation.py`, since removed — it swept `FUZZY_THRESHOLD`,
which no longer exists):

| ratio threshold | d=1 recall | d=2 | d=3 | overall | neg trip rate | traps |
|---|---|---|---|---|---|---|
| 76.0 | 1.000 | 0.857 | 0.867 | 0.909 | 0.267 | 4 |
| 80.0 | 1.000 | 0.643 | 0.667 | 0.773 | 0.200 | 3 |
| **84.0 (interim default)** | 0.800 | 0.500 | 0.467 | 0.591 | 0.067 | 1 |
| 88.0 (original default) | 0.667 | 0.500 | 0.267 | 0.477 | 0.067 | 1 |
| 94.0 | 0.200 | 0.143 | 0.000 | 0.114 | 0.000 | 0 |
| 96.0 | 0.067 | 0.000 | 0.000 | 0.023 | 0.000 | 0 |

No point on this curve reaches high recall *and* zero traps at once — the
best available trade tops out around d=1 0.80 with 1 trap still live (the
`reacts` → `react` false positive, confirmed directly: `reacts` is a real,
common English word, edit distance 1 from `react`, and no ratio cutoff can
tell "typo of a skill name" apart from "ordinary inflected verb" — they're
the same string-similarity fact.

**The fix: decouple recall from precision onto two different mechanisms**
(`matcher.py`):

1. `_max_edits_for_length()` — a fixed table (1 edit ≤6 chars, 2 ≤12, 3
   beyond) replacing the ratio threshold. This is what controls recall, and
   it no longer punishes short names.
2. A `wordfreq` gate — reject a fuzzy candidate if it's itself a recognized
   English word above a zipf-frequency cutoff, unless it's an exact
   taxonomy hit. This is what controls the trap rate, and it generalizes:
   real typos score 0.0 (unrecognized), while `was`/`get`/`code`/`reacts`/
   `trust` score 3.5–6.8. One mechanism catches all of them without hand
   -enumerating each one — `COMMON_WORDS` stays as a cheap fallback, not the
   primary defense.

Sweeping the new tunable (`evaluation/run_fuzzy_ablation.py`, now sweeping
the word-frequency cutoff instead of a ratio, since that's the axis that
actually trades off now):

| word-freq threshold | d=1 recall | d=2 | d=3 | overall | neg trip rate | traps |
|---|---|---|---|---|---|---|
| 1.0 | 0.933 | 0.571 | 0.333 | 0.614 | 0.000 | 0 |
| **2.0 (default)** | **0.933** | 0.571 | 0.333 | 0.614 | **0.000** | **0** |
| 3.5 | 0.933 | 0.571 | 0.333 | 0.614 | 0.000 | 0 |
| 4.0 | 0.933 | 0.571 | 0.333 | 0.614 | 0.133 | 2 |
| 6.0 | 0.933 | 0.571 | 0.333 | 0.614 | 0.267 | 3 |

Recall is flat across this sweep by design — the edit-distance table
controls that axis, not this one — and the trap rate is zero from 1.0 up to
3.5, with margin before the first trap re-appears at 4.0 (where `reacts`,
zipf 3.57, stops being treated as a real word). Default is set at 2.0,
comfortably inside that margin. **Target (d=1 recall > 0.90 with zero
traps) is met: 0.933 recall, 0 traps.** On the original 20-pair benchmark
this also came out ahead of the old design: full-taxonomy precision is back
to 0.980 (matching the original untuned 88.0 ratio default, and beating the
84.0 interim ratio default's 0.961), with strictly better typo recall.

d=2 (0.571) and d=3 (0.333) are still weak — two- and three-character
typos in short names remain hard to recover without loosening the edit
allowance enough to reopen false positives. Not addressed here; the
graded set makes the gap visible rather than hiding it inside a flat
20-pair average.

## What I removed, and why (semantic tier)

A third tier — embedding cosine similarity, `sentence-transformers`
(`BAAI/bge-small-en-v1.5`) — was built, wired into the matcher, and cut
after measurement. This section is the record.

**Why it looked necessary.** The 20-pair set can't evaluate a semantic
tier at all: tiers 1+2 alone already reach 1.000 recall on it, so any
match a semantic tier adds on top is a false positive by construction.
`evaluation/gold_semantic.json` was built to fix that — 22 positives phrased
so no literal skill name or fuzzy-distance surface form appears (e.g.
"orchestrated containerised workloads across a multi-node cluster" →
`kubernetes`), plus 20 hard negatives chosen to sit *close* to a skill in
embedding space without being it (e.g. "orchestrated a company-wide
reorganisation" is not Kubernetes). Building this set caught a real gap in
the taxonomy on its own: "brewed java for the team every morning" was
matching `java` — the beverage sense had no `ambiguous_forms` gate, unlike
`go`/`excel`/`spark`. Fixed, kept in `tests/test_skill_matcher.py`
independent of the tier-3 decision.

**The measurement.** With tiers 1+2 confirmed at 0.000 recall on the
positives (the set is genuinely hard by construction), sweeping
`SEMANTIC_THRESHOLD` against `bge-small-en-v1.5`:

| threshold | pos recall | neg trip rate | trap hits | spurious |
|---|---|---|---|---|
| 0.40 | 0.423 | 1.000 | 11 | 50 |
| 0.60 | 0.462 | 1.000 | 11 | 48 |
| 0.62 (was default) | 0.423 | 1.000 | 11 | 52 |
| 0.75 | 0.269 | 0.650 | 9 | 8 |
| 0.85 | 0.115 | 0.400 | 8 | 0 |

Recall never exceeds ~0.46, and the negative trip rate never drops below
0.40 anywhere recall is still usable. The bar was declared before the
numbers existed (`recall > 0.60` **and** `negative trip rate < 0.10`), and
no threshold clears it.

**Why it failed — architectural, not a tuning miss.** `_semantic_pass`
slid over every n-gram up to length 3 and took the max cosine against every
taxonomy label. On a 12-word sentence that's roughly 30 n-grams × ~110
taxonomy keys ≈ 3,300 comparisons, and the *maximum* of that many noisy
scores clears almost any fixed threshold almost always — a multiple
-comparisons problem no threshold fixes. Underneath that: short n-grams
don't carry meaningful embeddings. `bge-small` was trained on sentences;
feeding it 2–3 word fragments compares noise to noise. The unit of
comparison was wrong, not just the cutoff.

(This diagnosis is inferred from the shape of the curve, not from an
ablation of the mechanism itself — restricting candidates to noun chunks
and re-measuring would confirm or falsify it. Not done; didn't block the
decision to cut.)

**The call: cut it.** Removed `_semantic_pass`, the `Encoder` protocol, and
all encoder/`semantic_threshold`/vector-cache wiring from `matcher.py`.
Also removed, because they existed solely to serve that integration and
don't run against the trimmed matcher: `vector_cache.py`, `cache.py`,
`db.py`, `scripts/init_db.py`, and their tests
(`InMemoryVectorCache`/`NpyVectorCache`/`PgVectorCache` — see git history if
Phase 2 wants the pattern back; the reasoning for NpyVectorCache-over-Postgres
at this scale is preserved there). `evaluation/run_semantic_ablation.py`
was removed too, for the same reason — it constructs
`SkillMatcher(encoder=...)`, which no longer exists. **Kept:**
`embeddings.py` (`SentenceTransformerEncoder`, tested standalone in
`tests/test_embeddings.py`) and `evaluation/gold_semantic.json`, because
Phase 2 — bi-encoder retrieval over whole resume bullets, a different unit
and a different problem than per-n-gram cosine matching — will want a real
encoder and a paraphrase-labelled gold set again.

"I built a component, measured it against a bar set in advance, and
removed it when it didn't clear that bar" is the record this section is
for.

**Still open:** `gold_semantic.json`'s labels are a single-annotator first
draft — from the same annotator who designed the cases, which is exactly
the bias a labelling protocol exists to catch. A second, blind annotator
labelling the same 42 cases, with Cohen's κ reported, hasn't happened. This
needs an actual second human; the AI-driven majority of this module's build
generated the first labels, so it can't blind-check its own work here.

## Next

- [x] Wire `sentence-transformers` (`BAAI/bge-small-en-v1.5`) as a real encoder
- [x] Sweep the fuzzy tier's threshold on a gold set actually capable of
      measuring it, and fix what the sweep found (length-adaptive edit
      distance + word-frequency gate)
- [x] Sweep the semantic tier's threshold on a gold set actually capable of
      measuring it, and act on the result — cut tier 3, don't just flag it
- [ ] Recover d=2/d=3 fuzzy recall (currently 0.571 / 0.333) without
      reopening the trap rate — probably needs a second signal beyond edit
      distance + word frequency, not just a larger allowance
- [ ] Get a second annotator to blind-label `gold_semantic.json` and report
      Cohen's κ before reusing it in Phase 2
- [ ] Flag single-token skills whose lowercase form is a common English
      word (`ruby`, `swift`, `scala`, `dart`, `r`, `c`, ...) and gate them
      by default instead of requiring each to be hand-added like
      `go`/`excel`/`spark`/`java` were — ESCO will have thousands of these;
      `wordfreq` (already a dependency, now proven useful for tier 2) is a
      plausible mechanism for this too
- [ ] Download ESCO, swap the loader, re-run every benchmark above at 150×
      the vocabulary — something will break
- [ ] Wire this module into `ats_scorer.py` / `routes/resume.py` and delete
      the v1 substring scorer (still untouched, still what production uses)
- [ ] Phase 2: chunking, bi-encoder retrieval, cross-encoder rerank,
      nDCG@5 — over resume bullets and JD requirements, not taxonomy
      n-grams. `embeddings.py` and `gold_semantic.json` are the starting
      point.
