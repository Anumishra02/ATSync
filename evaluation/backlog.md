# ATSync scoring — evaluation backlog

Source of truth for what the 39-resume eval (`evaluation/labels.csv` vs
`evaluation/predictions.csv`, computed by `backend/scripts/resume_eval_*.py`)
found, and what it means to do about it. Numbers below are from the harness
after the bug-3 (heading segmentation/vocab) and bug-2 (uncomputable
quantification) fixes landed; bug-1 (hyphen-truncated bullets) is still
unpatched, on purpose (see its entry).

## Headline: the JD-match benchmark was contaminated, and the seed taxonomy can't read real postings

Two findings from rebuilding the JD corpus (full writeup: "JD corpus
rebuild" below) that outrank everything else in this document and belong
at the top, not buried in a subsection:

1. **The 92-term seed taxonomy matches ZERO skills in 20 of 33 real,
   currently-live job postings** — including postings squarely in the
   taxonomy's own target fields (a Neuralink electrical-engineering
   posting naming Altium and KiCad by name; RIVR's Mechanical Engineer
   posting; Figma's Product Designer posting). Checked directly via
   `matcher.extract(jd_text).skill_ids`, not inferred from a sample-size
   drop. This is a coverage failure, not a correlation problem, and any
   match-mode correlation number is secondary to it — a taxonomy that
   can't read most of the postings it's supposed to match against can't
   be fairly judged on how well it correlates with humans on the
   postings it happens to read.
2. **Every match-mode correlation number produced before this rebuild was
   measuring self-agreement, not performance.** The original 34-posting
   `jds.json` was written with the 92-term taxonomy already in view, so
   it happens to name exactly the vocabulary the taxonomy recognizes —
   0 of those 34 postings hit the coverage failure above. That's not a
   coincidence; it's the benchmark having been built with knowledge of
   the system under test. This is a contaminated-benchmark finding, the
   same failure mode that makes published ML results irreproducible, and
   it was only found by rebuilding the benchmark from a source
   (companies' own live job-board APIs) with no relationship to the
   taxonomy at all.

Confirmed prediction: filtered ESCO recovers coverage from 13/33 to
**32/33** on the identical real-postings set — not a ρ improvement, a
coverage one, exactly as predicted before running it (see the JD corpus
rebuild section). That reframes the taxonomy decision from "ESCO wins on
correlation" (it doesn't, clearly — see below) to **"the seed taxonomy
cannot process real job postings at all, and ESCO can,"** which is the
harder, more defensible, and more decision-relevant finding.

## The pattern across this whole cycle: one root cause, three unrelated-looking failures

Worth stating on its own, not left implicit across three separate
sections — this is the strongest argument in the project for why coverage
belongs as a headline metric next to accuracy, stronger than any single ρ:
**the same root cause (the seed taxonomy's near-zero vocabulary for
non-software fields) produced three failures that looked, at the time,
like three unconnected problems, in three different measurements:**

1. **Phase A, JD coverage**: 20 of 33 real, live postings match zero seed
   skills — including postings squarely in the taxonomy's own target
   fields. Symptom: a coverage number.
2. **Phase B, the mode asymmetry**: the fallback hybrid helps JD-match
   mode (ρ holds up while coverage triples) but measurably *hurts* no-JD
   mode (0.474 vs. seed's 0.716) — traced to the same seed-zero
   condition meaning something different on a JD (coverage gap) than on a
   resume (plausibly a true zero). Symptom: a sign flip in whether a fix
   helps.
3. **Phase C1, the contrast test**: 26 of 33 "wins" in a pre-registered,
   apparently-passing discrimination test turned out to be a coverage
   lottery — `score_resume` returns a structural 0.00 for the same
   zero-skill JDs, independent of the resume, so the true JD "winning"
   against 5 random ones measured nothing but whether the random draws
   happened to also be zero-skill. Symptom: a false positive in a test
   that was supposed to need no labels and carry no taxonomy dependency
   at all.

None of these three were found by looking for the taxonomy problem again
— each was found by taking a different measurement at face value, then
refusing to accept a result (a coverage number, a correlation gain, a
clean pass) without checking the mechanism behind it. That's the case for
coverage-as-headline-metric in one sentence: it wasn't one problem found
once, it was one problem that kept re-emerging as different-looking
symptoms until it was traced each time. A single blended quality score
would have shown three unrelated small anomalies, if it showed anything
at all; reporting coverage and correlation as separate, always-both-shown
numbers is what made the same root cause visible three times instead of
once.

## Phase A: four-way skill-extractor benchmark — coverage wins, correlation collapses

Distinct from the lexical ESCO-CSV comparison above (`Taxonomy.from_esco_csv`,
exact/alias string matching): this benchmarks three actual extraction
*mechanisms* — the seed taxonomy, `esco-skill-extractor` (sentence-embedding
cosine similarity against ESCO, threshold 0.6, untuned), and `skillNer`
(spaCy PhraseMatcher against the Lightcast/EMSI 31k-skill DB) — against the
same 33 clean (source_url-backed) JDs and 39 resumes. Script:
`backend/scripts/compare_extractors.py`; adapters in
`backend/services/skills/extractors.py`.

**Only 3 of the 4 planned candidates ran.** `ojd-daps-skills` pins
`numpy<2.0`, which has no prebuilt wheel for Python 3.13 and no C compiler
is available on this machine to build it from source — confirmed by
installing it in isolation, not inferred from the combined install
failing. Not worked around with `--no-deps` + a forced numpy 2.x: an
extractor whose behavior under an unsupported numpy is unverified is worse
than an absent one for a benchmark whose entire point is not trusting
unverified output. Documented as an environment blocker, revisit if this
ever runs somewhere with a compiler.

**Coverage (acceptance criterion — met):**

| | JD coverage (n=33) | resume coverage (n=39) | mean skills/doc, resume |
|---|---|---|---|
| seed | 13/33 (39%) | 33/39 (85%) | 4.6 |
| esco_embed | 31/33 (94%) | 38/39 (97%) | 9.7 |
| skillner | 33/33 (100%) | 39/39 (100%) | 45.7 |

**Correlation with human "skills" judgment — collapsed on both candidates.**
A4 explicitly called for re-checking whether the seed taxonomy's no-JD
ρ=0.653 survives under a wider-vocabulary extractor, "if it collapses, it
was proxying something else and that needs saying." It collapsed:

| | no-JD ρ (n=39) | JD-match ρ | tech ρ / non-tech ρ (no-JD) |
|---|---|---|---|
| seed | **+0.653** (p=0.000) | +0.519 (p=0.069, n=13) | 0.767 / 0.441 |
| esco_embed | +0.148 (p=0.369) | +0.199 (p=0.284) | 0.000 / 0.078 |
| skillner | +0.381 (p=0.017) | +0.045 (p=0.802) | 0.580 / 0.187 |

skillNer's tech/non-tech gap (0.393) is also *larger* than seed's (0.326),
not smaller — the acceptance criterion's second clause ("tech/non-tech gap
materially smaller than the seed baseline") is **not** met by either
candidate, only the coverage clause is.

**Wall-clock is independently disqualifying for skillNer**: mean 9.96s/doc
(median 3.3s), vs. seed's 19.6ms and esco_embed's 359ms. At that latency,
skillNer cannot run inline with a request regardless of its coverage or
correlation numbers.

**Mechanism, not just the number — a second construct-validity finding, same
shape as Experience's (see ExperienceScorer's docstring).** The rubric
defines skills as "named technical tools, languages and methodologies" —
concrete, nameable artifacts. The seed taxonomy is a list of exactly those
92 things. Its ρ=0.653 wasn't a happy accident; it was matching the
rubric's actual construct. ESCO's ~13.9k entries are overwhelmingly
competence statements ("manage records," "supervise a team") — real
labour-market skills, but not the construct this rubric's column is
scoring. Wider coverage of the wrong construct doesn't raise correlation,
it dilutes it: skillner's mean 45.7 skills/resume vs. seed's 4.6 is coverage
of a different question, not a better answer to the same one. Coverage and
signal are different axes; this benchmark is what separated them, and the
headline coverage finding above ("seed cannot read most real postings")
stands regardless — it's real, severe, and independently confirmed. What
this run adds is: **neither tested replacement is a clean fix for it.**
Wiring either one in as-is would trade a taxonomy blind on 61% of real
postings for one blind on 6%(esco)/0%(skillner) of postings but missing
most of the signal the seed taxonomy had on the postings it *could* read.

**Why coverage belongs next to accuracy as a headline metric, not
underneath it — the case for it, not just the assertion.** This is a run
where optimizing coverage *actively damaged* correlation (0.653→0.148),
not just failed to help it. A single blended "quality" score can't
represent that outcome at all — it would report a taxonomy swap as
strictly better (JD coverage 13→31/33) while hiding that it made the thing
the score claims to measure worse. Reporting coverage and ρ as two
separate, always-both-shown numbers is the only way this decomposition is
visible instead of averaged away.

**Not proceeding to Phase B ("wire the winner") on this data as a single
extractor.** See the hybrid result below instead — it's the more
decision-relevant finding this cycle produced.

### Threshold tuning (A4), on a held-out set disjoint from the 33

8 live Greenhouse postings (Asana, Gusto — neither company appears in the
33), fetched directly, provenance in
`evaluation/threshold_tuning_holdout.json`. Swept esco_embed's cosine
threshold 0.45–0.75 (`scripts/tune_esco_threshold.py`, one embedding build
reused across all thresholds via the library's own `_get_entity`, not
rebuilt per threshold).

**Finding: no threshold in this range cleanly separates signal from
noise — this is structural, not an unset hyperparameter, and it's better
evidence for the construct mismatch than any correlation number, because
it doesn't depend on n at all.** Verbatim, not paraphrased — this is the
paragraph to reuse in a write-up:

At the library default (0.60), esco_embed extracts exactly these 12
skills from the Asana Data Scientist posting (`asana_ds` in the holdout;
the posting names Python, Scala, SQL, statistics, machine learning,
experimental design, and distributed systems explicitly):

    ['SPARK', 'Scala', 'build predictive models', 'communicate with customers',
     'customer segmentation', 'data models', 'data warehouse',
     'gather experimental data', <unresolved ESCO URI>,
     'interact with users to gather requirements', 'liaise with engineers',
     'mathematics']

"SQL," "machine learning," and "statistics" — all *explicitly named in the
posting text* — are absent; they only appear at threshold ≤0.55.
"Python (computer programming)" is absent even at 0.55; it only appears at
≤0.50. Meanwhile "communicate with customers" and "liaise with engineers"
— generic competence phrases matching nothing this posting specifically
requires — clear 0.60 and persist. Lowering the threshold doesn't fix
this cleanly: at 0.50, the Field Marketing Manager posting (`asana_marketing`)
extracts, alongside the genuinely relevant "marketing management" and
"implement sales strategies," this same-threshold set:

    ['Perl', 'apply requirements concerning manufacturing of food and beverages',
     'assess the development of youth', 'develop production line',
     'emergent technologies', <unresolved ESCO URI>, 'implement sales strategies',
     'lead others', 'local area tourism industry', 'marketing management',
     'perform follow-up on pipeline route services', 'plan multi-agenda event']

"Perl" for a marketing role with no engineering content anywhere in the
posting; "assess the development of youth" and "apply requirements
concerning manufacturing of food and beverages" have no discernible
relation to it at all. Cosine similarity between phrase embeddings and
ESCO's skill descriptions does not reliably distinguish "this JD names
this skill" from "this text loosely resembles this skill's description,"
at any threshold tested, on either posting. This independently confirms
the construct-validity explanation above — it isn't a competing account,
it's the same finding demonstrated concretely and checkably rather than
inferred from a correlation drop. Picked 0.55 as a defensible middle
point for the hybrid below (better coverage than 0.60's near-total loss
on non-technical postings, without 0.45's flood) — not claimed as an
optimum, because none exists in this range.

### Hybrid (fallback, not merge): the strongest result in this benchmark

Per the exact test specified: score seed and ESCO as **separate**
sub-signals, and combine as a **fallback** — ESCO's match ratio is used
only when seed found zero skills in that JD; seed's ratio is used
whenever seed has one at all. This operationalizes "ESCO covers fields the
tool list can't reach," not "average the two." Script:
`scripts/hybrid_extractor_test.py`.

On the 33 clean JDs, seed found zero skills in 20 — ESCO (t=0.55) covered
all 20 of those.

| signal | n (coverage) | ρ | p |
|---|---|---|---|
| seed alone | 13/33 | +0.519 | 0.069 (not significant) |
| esco alone (t=0.55) | 33/33 | +0.277 | 0.119 (not significant) |
| **fallback (seed, else esco)** | **33/33** | **+0.451** | **0.008 (significant)** |

**Correction to how the p-values should be read**: 0.069→0.008 is NOT "the
same relationship, now with more statistical power" — that comparison is
invalid on its face, because seed-alone's n=13 and the fallback's n=33
aren't the same population. Seed-alone's 13 are a *biased subset*: exactly
the JDs where seed already found something, i.e. the easy cases by
construction. ρ=0.519 on that subset is an optimistic number that doesn't
generalize to match mode as actually used (where a JD's field isn't known
in advance to be one the taxonomy can read). ρ=0.451 on all 33 is what
match mode actually does, on the full, honest sample.

**So the hybrid didn't cost accuracy — it revealed that seed's number was
measured on the subset where seed happens to work.** That's the correct
argument for the hybrid, not the p-value comparison, and it's the one that
survives a follow-up question: ρ=0.519 was never a fair estimate of
match-mode performance; ρ=0.451/n=33 is the first trustworthy one this
project has produced for that mode.

**Sub-signals are cleanly separable, confirmed by construction, not just
empirically similar**: re-reading `hybrid_extractor_test.py`'s branching —
`elif esco_jd` is only reached when `if seed_jd` is false, so the
fallback's value on every one of the 13 seed-covered JDs is computed by
the exact same expression (`len(seed_jd & seed_res_sets[rid]) /
len(seed_jd)`) as seed-alone. The fallback can never override seed with a
weaker ESCO reading; it only ever fires where seed has no reading at all.
This is what makes the architecture defensible as a design, not just as a
measured outcome — the two layers' contributions can be reported and
reasoned about independently, because they never blend.

**Recommendation, not yet acted on**: the fallback hybrid (seed primary,
ESCO t=0.55 fallback-only) is the best-supported default for JD-match
mode skill scoring measured so far — not because it beat seed's number,
but because it's the first honest one. Wiring it in is Phase B work,
deferred per this cycle's scope, but this is what "wire the winner" should
wire — not seed alone (misses 20/33 JDs entirely, and its apparent
strength was measured only on the JDs it doesn't miss) and not esco alone
(loses seed's construct-matched precision on the 13 it could already
read).

**The 13-vs-20 split — is ESCO's contribution real, or is the hybrid seed
plus coverage padding?** ρ on the 20 JDs where only ESCO fires (its
contribution in isolation, not blended with seed's 13): **n=20, ρ=+0.246,
p=0.296.** This is NOT distinguishable from zero (p=0.296 fails
significance same as the no-JD n=6 result below) — it would be overclaiming
to call this "a real but noisy contributor." The defensible claim isn't
about ESCO's isolated contribution at all: it's that the fallback takes
match mode from 13/33 measurable to 33/33 measurable **while correlation
holds up rather than collapsing** (0.519→0.451, not 0.519→0.1 or negative).
Coverage is the win here, exactly as A3 said to report it as the headline
— correlation not collapsing under 2.5x the coverage is the supporting
evidence, not a second, independent win layered on top of it.

**Phase B question, resolved: hybrid for match mode only, NOT no-JD mode.**
The no-JD ρ=0.653 in the original Phase A benchmark was measured on
resumes with seed alone and had never been run through this fallback
architecture — checked before recommending anything, per your instruction,
not assumed to transfer from the match-mode result:

| signal | n | ρ | p |
|---|---|---|---|
| seed alone, seed-covered resumes (33/39) | 33 | +0.716 | 0.000 |
| esco alone, seed-zero resumes only (6/39) | 6 | −0.088 | 0.868 |
| **fallback (seed count, else esco count)**, all 39 | 39 | **+0.474** | **0.002** |

**The fallback measurably hurts no-JD mode** — 0.474 (n=39, p=0.002) is
worse than both the original blended measurement (0.653) and seed's own
covered-subset number (0.716, n=33, p=0.000). That comparison is
well-powered on both sides and is the load-bearing evidence for not
extending the hybrid here — not the n=6 ESCO-alone slice by itself.
Caveat on that slice, stated precisely rather than overclaimed: ρ=−0.088
(n=6, p=0.868) is indistinguishable from noise in *both* directions — it
does not establish that ESCO adds nothing on resumes, only that no
contribution is detectable at n=6. The burden is on the change to justify
itself, and at n=6 it hasn't; that is a different, weaker claim than "ESCO
replaces signal with noise," and the backlog should carry the weaker one.

Mechanism (this part the well-powered comparison does support): on a JD,
a seed zero is a coverage gap — the posting almost certainly names *some*
real requirement, seed just can't read the phrasing. On a *resume*, a
seed zero is plausibly a real, informative zero: the rubric defines
skills as "named technical tools, languages and methodologies," and a
resume that names none is exactly what a human rater would also mark low
on this dimension. Same signal, opposite meaning depending on which
document it comes from — that asymmetry, not the n=6 point estimate, is
what earns the mode-specific default.

**Net Phase B scope**: wire the fallback hybrid (seed primary, ESCO
t=0.55 fallback) for JD-match mode only. Leave no-JD mode on seed alone,
unchanged.

**Implementation note for Phase B, to get right at wiring time, not
after**: the mode asymmetry above must live in *configuration* — which
extractor(s) a mode is allowed to fall back to, and whether fallback is
enabled at all — not as a branch inside `SkillsScorer`'s own logic
(`if mode == "jd_match": try esco fallback` hardcoded in the scorer). If
extractor choice is a parameter the mode declares (e.g. each mode's config
lists its primary extractor and an optional fallback extractor +
threshold), adding a third mode later, or re-running this benchmark
against a changed taxonomy or a newly-available candidate (ojd-daps-skills,
if the numpy blocker ever clears), stays a config change and a benchmark
re-run. If the asymmetry is hardcoded as a branch inside the scorer, every
future change to it requires touching scorer logic again, and the two
modes' behavior drifts apart in code that isn't obviously about "which
extractor does this mode use" — the exact kind of coupling this cycle's
whole benchmark exists to keep measurable and swappable.

**ojd-daps-skills remains untested for environment reasons, not merit
reasons** — worth stating plainly rather than letting the gap read as a
verdict. It's the one candidate in the original four designed specifically
to map free-text phrases onto a taxonomy (ESCO or Lightcast) while handling
terms the taxonomy itself lacks — closest in spirit to the fallback hybrid
just built by hand here, and plausibly a single-package version of it. The
blocker is `numpy<2.0` having no Python 3.13 wheel on a machine with no C
compiler, not anything about the library's design. If a Python 3.11
environment is ever cheap to stand up, re-running Phase A's four-way
benchmark with it included is worth doing before assuming the hand-built
hybrid is the ceiling.

**ojd-daps-skills remains untested for environment reasons, not merit
reasons** — worth stating plainly rather than letting the gap read as a
verdict. It's the one candidate in the original four designed specifically
to map free-text phrases onto a taxonomy (ESCO or Lightcast) while handling
terms the taxonomy itself lacks — closest in spirit to the fallback hybrid
just built by hand here, and plausibly a single-package version of it. The
blocker is `numpy<2.0` having no Python 3.13 wheel on a machine with no C
compiler, not anything about the library's design. If a Python 3.11
environment is ever cheap to stand up, re-running Phase A's four-way
benchmark with it included is worth doing before assuming the hand-built
hybrid is the ceiling.

## Cycle close-out: four numbers

**1. Post-fix not-covered ρ: −0.182 (n=28, p=0.355).** Still not
significant, still inverted rather than merely weak.
`ρ(lost_share, human_total) = +0.105 (p=0.596)` already ruled out "stronger
resumes lose more taxonomy credit" as the mechanism — this is noise from
`jd_skill_count` being 1–5 for nearly all not-covered fields, not a real
effect. No action item here beyond "grow the taxonomy" (already tracked
separately, not re-litigated in this backlog).

**2. Achievements, recomputed on the 9-in-both set (R11 excluded from both
sides, so the comparison isn't distorted by R11 dropping out post-fix):**
mean signed gap **−38.44 → −31.33**. The ~7-point improvement from the
chunker fix is real and robust, not a sample-composition artifact — if
anything, the effect is slightly larger than the originally-reported
−35.40 → −31.33 (which mixed in R11's pre-fix value at a small −11 gap that
was flattering the pre-fix average).

**3. Covered coverage drop (10/10 → 9/10) is entirely R11, confirmed at the
chunk level:** R11 has 0 `ChunkKind.BULLET` chunks (24 prose, 3 heading) —
a genuinely bullet-free, prose-paragraph resume. The bug-2 guard fired for
the reason it exists to fire for, not as a side effect of anything else.
Not a regression.

**4. Per-dimension slope/intercept regression (covered set, human% vs
machine%, OLS):**

| dimension | n | slope | intercept | r² | p |
|---|---|---|---|---|---|
| skills | 10 | 1.068 | −41.58 | 0.625 | 0.0065 |
| achievements | 9 | 0.788 | −16.85 | 0.712 | 0.0043 |
| structure | 10 | 0.466 | +43.37 | 0.351 | 0.0710 |
| relevance | 10 | 0.105 | +32.96 | 0.018 | 0.7100 |
| writing | 10 | 0.188 | +25.00 | 0.016 | 0.7272 |

This splits the "uniform −35 across four dimensions" framing into two
categorically different problems, and reprioritizes item 4 below:

- **skills and achievements track human judgment for real** (slope ≈ 1 and
  ≈0.8, r²=0.63 and 0.71, both significant at p<0.01) **but sit well below
  where a 1:1 relationship would put them** — a large negative intercept
  with a near-1 slope is exactly the signature of a floor/no-baseline-credit
  mechanism, not noise. These are the two dimensions a calibration fix can
  actually fix.
- **relevance and writing carry no reliable signal at all** (slope ≈ 0.1–0.2,
  r² ≈ 0.02, p ≈ 0.7 — indistinguishable from flat). A calibration offset
  does nothing for a proxy that isn't tracking the target variable in the
  first place. These need the underlying metric replaced, not recalibrated
  — consistent with the R38 trace finding that `check_repetition` penalizes
  legitimate technical-term repetition as "bad writing," and with
  `keyword_score`'s plain word-overlap having no concept of what a human
  means by "relevant."
- structure is in between (slope 0.47, r²=0.35, p=0.071 — suggestive, not
  significant at n=10).

## Prioritized next work

**Note**: items 1–5 below predate Phase A/B/C1 and several have since been
superseded or completed (item 1 is done — see the Phase B design note's
regression-gate reference; item 2 is done — see "Phase 1 item 1: rebuild
ExperienceScorer" in git history). The live front of the queue is:
**Phase B (fallback hybrid for JD-match mode + a `score_resume`
uncomputable guard for zero-skill JDs, built alongside it — see Phase C1's
"second bug" note), then Phase C1 re-run against the hybrid.** Kept below
for the items still genuinely open (4, 5) rather than rewritten.

### 1. Regression gate (`make eval` + CI)
Turn the hand-run/hand-interpreted Step 3 into a committed contract:
`make eval` writes `evaluation/metrics.json` (per-dimension gaps, coverage,
ρ with its CI), and CI fails on **coverage regression** or **per-dimension
gap moving past a threshold in the wrong direction**. Not ρ — too noisy at
n=10/28 to gate on (this cycle's own CI on covered ρ spans −0.23 to +0.96).
Coverage and gap direction are stable enough to be contracts; without this,
the next refactor silently undoes the chunker fix and it surfaces three
months later instead of in a PR.

### 2. Experience scorer (new feature, not a defect fix)
20 of the human rubric's 100 points, and ATSync has no scorer for it at
all — the only backlog item that's a missing capability rather than a bug.
Every calibration number produced until this exists is measured on a
truncated 80-point scale. Largest single piece of remaining work; deferred
through this entire cycle on purpose so the defect-fixing work wasn't
blocked on it.

### 3. Calibration mechanism — skills and achievements only
Per the regression above, this is NOT "fit an offset on these 38 resumes"
(that would be fitting noise, and the user-visible defect — a human-75
resume scoring 40 — is real and worth a mechanism explanation, not a patched
constant). Working hypothesis: both scorers award points only for evidence
they can positively detect (a matched skill, a bullet with a digit), with
no baseline credit for a resume that's competent but doesn't happen to
phrase things in exactly the detectable form — so absent-detection reads as
absent-quality. Confirm the mechanism per-scorer before changing weights:

- `skill_score` (services/scoring.py `legacy_ats_score`): does a resume that
  paraphrases a required skill instead of naming it get zero credit for
  that skill, with no partial/semantic-match credit at all?
- `check_quantification` (services/analyzer.py, post-chunker-fix): does a
  bullet with real, undeniable impact but no literal digit (e.g. "led the
  team to its best-ever quarter") get zero credit, with no partial credit
  for qualitative-but-strong impact language?

**relevance and writing are excluded from this item** — they don't floor,
they're uncorrelated, and a calibration fix would be invisible on them. See
item 4.

### 4. Replace, not recalibrate, the relevance and writing proxies
`keyword_score` (plain 4+-letter-word overlap) and `check_repetition`
(flag any 5+-letter word appearing ≥4 times) don't need their floor raised
— they need to measure something closer to what a human rubric-reader
means by "relevance" and "writing quality" in the first place. Concretely
lowest-effort candidates: relevance via the richer, evidence-linked
`score_resume`/`SkillMatcher` machinery that already exists but isn't
wired into the live route yet (`services/scoring.py`'s own docstring flags
this gap); writing via distinguishing domain-vocabulary repetition
(legitimate — see the R38 trace) from actual word-choice repetition.

### 5. Ship "can't assess" to the frontend
Bug 2's uncomputable guard exists in the backend only. 11/38 resumes in
this eval produce no achievements signal at all (29% of the corpus) — the
UI currently has no way to know that and would render whatever value it's
handed. Small, and it's the explainability claim actually delivered rather
than asserted.

## Deferred

**Bug 1 (mid-word-hyphen bullet truncation, `check_quantification`'s old
regex).** Shares the chunker fix that already landed for bug 3 — some of
its effect may already be resolved as a side effect. Re-measure against
the current chunker before patching it as a separate change; don't spend a
cycle on it independently.

## Construct validity: mechanically-faithful scoring vs. human judgment

Two dimensions now, independently, show the same shape of finding, and
it's worth naming as a pattern rather than re-discovering per-dimension:
a scorer built faithfully to a rubric's own *stated* criteria can
correlate weakly with the human score on that dimension, not because the
implementation is wrong, but because the human's actual grading behavior
evidently weighed something the stated criteria don't capture.

**Writing** (`WritingScorer`): repetition + passive voice + filler
density, rewritten from a repetition-only proxy after a defect-injection
suite (`test_writing_discrimination.py`) proved the old proxy blind to
passive voice and filler entirely. The new proxy passes all 40
defect-injection tests (genuinely discriminates on the three things it
checks) and still measures essentially zero correlation with the human
label: rho=-0.011 (p=0.95, n=39) after every fix found, including the
fact-listing exclusion below. R11 is the concrete case: a human scored it
7/15 (middling); the proxy gives it a perfect 15.0 — zero repeated words,
zero passive lines, zero filler lines detected, and a human still found
something worth marking down.

**Experience** (`ExperienceScorer`): built directly against the rubric's
own five stated mechanical facts — org name, job title, city/state, dates
per entry, reverse-chronological order — "parseable, not semantic" by
design. Measured against the human "experience" column: rho=0.214
(p=0.20, n=38), also not significant. The rubric column itself is titled
"depth and relevance of roles," but every criterion actually listed under
it is formatting completeness — a mismatch between the column's name and
its own stated definition. The clearest disagreements confirm this
directly: R14 and R10 are Canva templates where the experience section's
bullets are literal, unfilled "Lorem ipsum dolor sit amet..." placeholder
text — a human correctly scored them near the bottom (4/20, 7/20) while
the scorer gives them 12/20 each, because their headers (org, title,
dates) are genuinely well-formed even though there's nothing behind them.
R13 is starker: one entry, zero bullets, every header fact present — 20/20
mechanically, 8/20 from the human.

**The decision, deliberately not the more thorough one:** the more
rigorous fix would split each dimension into a `_completeness` sub-score
(what's built, keep it) and a `_substance` sub-score (semantic, needs a
different method — likely the same grammar/clarity signal both
docstrings point to). That's real future work, not done here, because it
changes the rubric's shape mid-flight and breaks comparability with the
39 frozen labels this whole cycle is measured against. What's done
instead: keep both scorers exactly as built, report the weak correlation
honestly in each one's docstring, and do NOT tune either proxy toward the
labels to make the number look better — that's the one move that would
make the metric improve and the project worse, since neither proxy would
actually be measuring what a human meant by the dimension's name.

**One mechanism check performed before filing this, not skipped:**
Achievements' fact-listing exclusion (`FACT_LISTING_PATTERN`, promoted to
`chunking.py` and made public once it was needed by a second scorer) was
checked against both Writing and Skills before assuming it only applied
to Achievements.
- **Writing**: the same category error applies on mechanism grounds (a
  "Coursework: ..." line isn't real prose a human would judge for passive
  voice or filler either) and was applied. Checked its effect: only 6/39
  resumes' scores changed at all, and rho moved from -0.040 to -0.011 —
  noise, not a fix. Applied anyway for mechanism-correctness, not because
  it closes the gap; it doesn't, which is itself the confirming result
  that Writing's problem isn't a fixable denominator bug like
  Achievements' was.
- **Skills**: does NOT apply, checked empirically rather than assumed —
  excluding fact-listing lines from skill extraction loses real,
  correctly-recognized skill matches on 15/39 corpus resumes (a "Computer
  skills: Excel, SQL" or "Languages: Spanish" line is exactly where people
  legitimately declare skills). Left unchanged.

## ESCO taxonomy swap (Phase 1 item 2)

Brief, before doing anything: keep the loader pluggable and produce the
before/after comparison as the actual deliverable, not the swap itself;
confirm the JD corpus is independent of ESCO before trusting any
match-mode number. Both conditions confirmed before running anything:
`Taxonomy.from_esco_csv` already existed behind the same interface as
`from_seed_json` (no new plumbing needed); `evaluation/jds.json` (the
34 field-matched JDs used below) was committed in an earlier session,
before `backend/data/skills_en.csv` existed anywhere in this repository
or its working tree — verified via `git log --diff-filter=A --
evaluation/jds.json` — so the JD text cannot have been drawn from ESCO's
own skill descriptions.

**Downloaded the real thing, not a stand-in.** ESCO v1.1.1 classification
(English), fetched from the European Commission's official distribution
(see `backend/data/README.md`): 13,896 skills, 98,067 surface forms — the
"~13.9k" figure Phase 1's brief anticipated, confirmed, not assumed.

**First measurement: a naive swap is a regression, not an upgrade.**
Ran `SkillsScorer` (no-JD count mode) against the human "skills" label on
all 39 corpus resumes, seed taxonomy vs. raw ESCO:

| taxonomy | n | slope | intercept | r² | ρ | p |
|---|---|---|---|---|---|---|
| seed (92 terms) | 39 | 0.954 | −4.94 | 0.438 | **0.653** | <0.001 |
| ESCO, raw | 39 | 0.135 | 12.88 | 0.056 | 0.212 | 0.196 |

Worse on every axis, and on the tech-field subset (n=7 — Data Science,
SWE, Full-Stack, etc.) it's not just worse, it's *flat*: every tech resume
saturates the scorer's max, ρ undefined (constant output). Diagnosed, not
guessed: ESCO's much larger alias set includes many single generic
English words loosely attached to a far narrower concept —
`"engineering"` aliases to *packaging engineering*, `"processes"` to
*perform ground-handling maintenance procedures*, `"measurement"` to
*metrology* — plus real but out-of-domain entries (`"dancing"`,
`"soccer"`) that are genuine ESCO skills, just noise for a resume's
professional-skill score. Concrete case: R26 (Materials Science ->
Consulting, human skills score = 3/15, the *lowest* in the corpus)
matched `engineering`, `processes`, `measurement`, `interaction`,
`dancing`, `soccer` as "skills" under raw ESCO — none of them a real
signal about this résumé.

None of this is the fuzzy-tier typo problem `matcher.py`'s existing
`wordfreq` gate already guards against — every one of these lands as
`MatchTier.EXACT`, because it's baked into the taxonomy's index as a
literal surface form. The gate that exists protects against *near-misses*
on real skill names; it was never asked to protect against the skill
names themselves being too generic, because the 92-term seed was small
enough that every alias was hand-picked and this never came up.

**Fix: `Taxonomy.from_esco_csv(..., filter_generic_aliases=True)`** (now
the default) drops a single-word surface form when it's both long (≥5
characters) and common (zipf ≥ 4.0). The length gate is load-bearing, not
decoration — a length-blind frequency cutoff nearly reintroduced, in a
worse form, the exact "`go` the language vs. the verb" ambiguity this
project already solved once: `"r"` (zipf 5.35) and `"go"` (zipf 6.03) are
both real, short language names that a naive filter would have dropped
from the taxonomy *entirely*, not merely fuzzy-gated. Verified `r`,
`java`, `sql`, `python` all still resolve correctly after filtering (see
`tests/test_taxonomy_esco.py`).

Re-measured:

| taxonomy | mode | n | ρ | p |
|---|---|---|---|---|
| seed | skills, no-JD | 39 | 0.653 | <0.001 |
| ESCO, filtered | skills, no-JD | 39 | 0.496 | 0.001 |
| seed | skills, JD-match | 39 | 0.294 | 0.070 |
| ESCO, filtered | skills, JD-match | 38 | **0.477** | **0.002** |
| seed | relevance | 39 | 0.089 | 0.592 |
| ESCO, filtered | relevance | 39 | 0.232 | 0.155 |

Two different stories, not one:
- **JD-match mode — the mode that matters most in production — genuinely
  improves**, and clears significance where the seed taxonomy doesn't
  (ρ 0.294→0.477, p 0.070→0.002). Relevance moves the same direction,
  though not far enough to clear significance at n=39.
- **No-JD count mode does not clearly improve overall**, and on the
  tech-field subset (n=7) it stays essentially flat (ρ≈0.00) regardless
  of `_SKILLS_NO_JD_TARGET_COUNT` — checked across target=8 through 30,
  not assumed fixed by one value: no target recovers a real ranking,
  because the underlying per-resume ESCO counts just don't order that
  small subsample the way the human label does (R24, the *lowest*-scored
  tech resume, has the *second-highest* raw count). n=7 is too small to
  tell "genuinely noisy at this scale" apart from "a real defect" — this
  needs more tech-field labels before concluding either way, not more
  target-tuning on the same seven data points.

**Decision, not yet made here:** filtered ESCO is a measured, significant
win for match-mode skill scoring and a wash-to-regression for the no-JD
count mode on tech resumes specifically. Recommending the swap for
match-mode while keeping the seed taxonomy as the no-JD default (per
scorer, or per mode) is the option this data actually supports — not a
blanket swap either direction. `filter_generic_aliases=True` is the
default either way; anyone loading ESCO from here forward gets the
filtered version unless they deliberately opt out (see
`backend/data/README.md`). Not wired into the live route's default
taxonomy as part of this item — that's a product decision on top of a
measurement, not a continuation of it.

See `backend/scripts/compare_taxonomies.py` for the full runnable
comparison (seed / raw ESCO / filtered ESCO, three-way, on-demand) and
`backend/services/skills/taxonomy.py`'s `from_esco_csv` docstring for the
filter's own reasoning inline with the code it changes.

## JD corpus rebuild: the real bottleneck was upstream of the taxonomy

Flagged before the ESCO work above was trusted: seed-taxonomy skills/JD-match
(ρ=0.294, p=0.070) scored *worse* than seed-taxonomy skills/no-JD
(ρ=0.653, p<0.001) on the same 92 terms — backwards, since adding role
context should help, not halve the correlation. Two candidate causes:
`jds.json`'s 34 postings are field-only (no seniority match, level-blind
against ten distinct levels in the corpus), or JD-mode's conditioning
logic itself destroys signal by capping credit to a thin JD term list.

**Rebuild.** One real, currently-live posting per resume (not per field),
matched on field *and* level from `evaluation/labels.csv`, fetched
directly from each company's own public job-board API (Lever
`api.lever.co/v0/postings`, Greenhouse `boards-api.greenhouse.io`) on
2026-08-26 — `evaluation/jds_v2.json`, provenance (source URL, company,
title, fetch date) recorded per entry. **The evaluation set is n=33, not
n=38**: 5 resumes (R02, R04, R07, R09, R18) have no live posting collected
(`collected: false`, `text: null`) and are dropped from the set outright
rather than backfilled with the old field-only JD — backfilling would
silently mix a taxonomy-friendly-by-construction JD into the same n as
genuinely independent postings, contaminating exactly the comparison this
rebuild exists to make. Of the 33: 27 real and well-matched, 6 real but
with a noted level mismatch (`note_imperfect_match` per entry — e.g. R32
got a senior owner's-rep PM role against an "early-career" label; the
live-posting market didn't have a clean fit in the time available).
Smaller and clean beats larger and mixed.

### Coverage, not correlation, is the headline (see top of document)

Checked directly via `matcher.extract(jd_text).skill_ids`, not inferred
from a sample-size drop:

| taxonomy | JDs with ≥1 matched skill (of 33) |
|---|---|
| seed (92 terms) | **13/33** (39%) |
| ESCO, filtered | **32/33** (97%) — recovers 19 of the 20 seed zero-match JDs |

Seed's 20 zero-match postings include ones squarely in its own target
fields: Neuralink's EE posting (names Altium and KiCad by name), RIVR's
Mechanical Engineer posting, Figma's Product Designer posting. This is
the confirmation of the prediction made before running the comparison:
*"the expected effect isn't a ρ improvement — it's a coverage
improvement."* It was. **This reframes the taxonomy decision: not "ESCO
wins on ρ" (see below — it doesn't, on either taxonomy's own covered
subsample) but "the seed taxonomy cannot process real job postings at
all, and ESCO can."** That's the harder, more defensible finding, and it
settles the mode-specific recommendation the earlier ESCO section
deferred: ESCO for match-mode, full stop, on coverage grounds alone,
independent of what ρ does next.

### Resume-side coverage check (same 92 terms, no-JD skills mode)

If 20/33 real JDs match nothing, the same taxonomy applied to *resumes*
— the population `ρ=0.653` (no-JD skills mode) was measured entirely
against — could plausibly have the same blind spot. Checked directly,
not assumed clean by association:

33/39 resumes match at least one seed-taxonomy skill; 6 match zero —
R04, R15, R25, R27, R28 (already separately documented — CORRECTION, see
Phase D below: this was originally called an extraction-readability
case/font-encoding corruption, checked directly with pymupdf and that's
wrong; R28's text extracts cleanly, the actual failure is a merged
heading defeating chunking.py's heading-shape gate, downstream of
extraction, not a readability problem), R32. Their human "skills" scores: R04=12,
R15=7, R25=9, R27=6, R32=8 (all out of 15) — not uniformly low. **R04 in
particular is a real miss: a resume a human scored 12/15 gets a flat
machine 0**, because `SkillsScorer`'s no-JD "count" mode never goes
uncomputable (`min(0/12, 1.0)*15 = 0` is still a valid score, not `None`)
— so, unlike the JD-side collapse, this doesn't shrink `ρ=0.653`'s n or
introduce selection bias. It IS a real, quantifiable blind spot baked
directly into that number: roughly 15% of resumes get scored purely on
the strength of whether the taxonomy happens to name their skills, with
at least one clear case (R04) where it doesn't and the human clearly
disagreed. `ρ=0.653` is not invalidated by this the way skills/JD-match
was — no hidden exclusion — but it is not as clean as reported without
this caveat attached, and the fix is the same one already underway:
taxonomy coverage.

### Correlation, on each taxonomy's own covered subsample — selection bias is real, read these numbers accordingly

**Every ρ below is computed only over the JDs that produced a score at
all** (`SkillsScorer`'s JD-match mode is uncomputable, not zero, when the
JD names no recognized skill) — for seed that's the *easiest* 13 of 33
real postings, the ones whose language happens to overlap the 92-term
list; for ESCO it's 32 of 33, close to the full, representative set.
**These are not comparable samples, and neither ρ should be read as a
neutral estimate of match-mode performance — seed's is optimistic
(cherry-picked easy cases), ESCO's is closer to real but still small.**

| taxonomy | JD set | mode | n | ρ | p |
|---|---|---|---|---|---|
| seed | OLD field-only (contaminated) | skills/JD-match | 39 | 0.294 | 0.070 |
| seed | NEW real (13/33 covered) | skills/JD-match | 13 | 0.519 | 0.069 |
| ESCO, filtered | OLD field-only (contaminated) | skills/JD-match | 38 | 0.477 | 0.002 |
| ESCO, filtered | NEW real (32/33 covered) | skills/JD-match | 32 | 0.185 | 0.312 |
| seed | OLD field-only | relevance | 39 | 0.089 | 0.592 |
| seed | NEW real (33) | relevance | 33 | 0.215 | 0.229 |
| ESCO, filtered | OLD field-only | relevance | 39 | 0.232 | 0.155 |
| ESCO, filtered | NEW real (33) | relevance | 33 | **0.387** | **0.026** |

Two things worth naming here, not just the coverage headline:
- **ESCO's skills/JD-match ρ on its own near-complete covered set (0.185,
  n=32) is neither better nor worse than seed's on its cherry-picked
  n=13 (0.519) in any meaningful sense — they're not the same
  measurement.** Seed's number describes 13 easy cases; ESCO's describes
  almost the whole real distribution, including the hard ones seed never
  even attempted. A lower ρ on a harder, more complete sample is not a
  regression.
- **ESCO's relevance ρ against the real JD corpus (0.387, p=0.026) is the
  one genuinely significant number in this entire match-mode
  investigation, old or new JDs, either taxonomy.** Worth flagging as a
  real, positive, replicated-once signal — not over-claiming from a
  single significant result at this sample size, but it's the strongest
  data point for adopting ESCO on the relevance dimension specifically,
  on top of the coverage case already made above.

Every ρ number in this section carries `n≤33` and the selection-bias
caveat above; treat all of them, including the "significant" ones, as
directional, not conclusive, until re-measured on a larger corpus.

### What's still open

- **R27 (Urban Political Economy) remains zero-match even under ESCO**
  — its `note_imperfect_match` already flags the underlying posting
  (Civitech's general civic researcher role) as a weak field fit; this
  is likely that mismatch surfacing again, not a new taxonomy gap.
- The 5 uncollected resumes (R02, R04, R07, R09, R18) stay uncollected;
  deliberately not chased further — see the top-level decision to keep
  the eval set clean at n=33 rather than backfilled and mixed.
- No live-default change to either the taxonomy or the JD-match
  conditioning logic has been made from any of this. Coverage is now the
  documented, decision-relevant reason to prefer ESCO for match-mode;
  whether and how to wire that in is a separate product decision.

## Phase C1: relevance contrast test — pre-registered before running

Relevance has been weak under every configuration measured so far
(0.089–0.232, never significant) and survived the `score_resume` switch —
three independent measurements pointing the same direction. This tests
something different: not "does relevance rank 33 resumes the way a human
would," but "can it tell a matched JD from a random one at all." Written
down before `scripts/relevance_contrast_test.py` was run, not after.

**Implementation under test**: `RelevanceScorer`
(`services/analysis/scorers.py`), which wraps `score_resume` — the
current build. The historical 0.089–0.232 figures span both this and the
earlier `legacy_ats_score`/`keyword_score` version; this result belongs
specifically to `score_resume`, stated so it isn't read as settling
anything about the earlier implementation.

**Criterion**: per-resume win rate, not mean difference or a correlation
of ranks. For each of the 33 clean-JD resumes: score the resume against
its own true JD plus 5 randomly-drawn JDs from the other 32 (fixed seed
20260830, without replacement, none equal to the true JD) — 6 candidates.
Win = the true JD's score is the max (ties count as a win) among all 6.

**Null, explicit**: if the proxy carries no real matching signal, the true
JD ranks #1 of 6 purely by chance — p₀=1/6, expected 5.5/33 wins.

**Pass threshold, computed before running**: one-tailed binomial test
against p₀=1/6, α=0.05 → **≥10/33 wins** (P(X≥10)=0.038 under the null).
Not a round number chosen for optics — the smallest count that clears
significance.

**Prediction being tested, stated before the result is known**: relevance
may pass this test (discriminate a matched JD from a random one cleanly)
while still correlating weakly with human labels in the regression sense.
These are different claims — binary separation between a good and a bad
match is an easy problem; fine-grained ranking of 33 resumes by *degree*
of fit against their own JDs is a hard one. If that split is what's found
— contrast test passes, regression stays flat — the proxy isn't broken;
the flat regression is range restriction (the proxy compresses everything
in the "plausible match" region together), and the fix is a threshold or
rescaling problem, not evidence the embedding/matching mechanism itself
needs rewriting. If the contrast test also fails, that's a different,
worse finding — the proxy carries no usable signal even at the coarse
grain, and rewriting is the right response after all.

**Result — the pre-registered test technically passes, but it's
contaminated, and the contamination is worth more than the pass.**

Literal reading: 24/33 wins, binomial p≈0.0000, clears the ≥10/33
threshold by a wide margin. That is NOT the number to report, and here's
what running it (rather than assuming it was clean) found: **26 of the 33
true JDs score exactly 0.00.** `score_resume` (services/scoring.py)
returns a structural zero whenever a JD has no seed-recognized skills at
all (`total=0 → score=0` by construction) — independent of the resume
entirely. Checked directly: those 26 zero-scoring JDs are exactly the same
20-JD zero-seed-skill set from Phase A (`R01, R03, R05, R06, R08, R10,
R11, R12, R13, R15, R17, R21, R23, R24, R26, R27, R32, R34, R35, R39` —
20 of the 26; the remaining 6 zero-true-score cases are skill-having JDs
whose specific required skills this particular resume just doesn't have,
a real negative, not a coverage artifact). For a zero-true-score resume,
"win" depends on whether any of the 5 random draws happens to be a
skill-having JD with *incidental* content overlap against this resume —
unrelated to whether the resume matches its own field. That's not
measuring discrimination; it's re-exposing the same taxonomy-coverage gap
Phase A already found, in a test that was supposed to need no labels and
carry no such confound.

Splitting the result by whether the true score was structurally forced to
zero:

| subset | n | wins | note |
|---|---|---|---|
| zero-true-score (structural) | 26 | 19 | contaminated by Phase A's coverage gap, not informative |
| **nonzero-true-score (genuine)** | **7** | **5** | `R16, R19, R30, R31, R33` win; `R37, R38` lose |

**The honest reading**: the contrast test as designed is only genuinely
computable for 7/33 resumes — the same ~21% of the corpus the seed
taxonomy can read at all. 5/7 wins on that subset is suggestive of real
discriminative ability but n=7 cannot support any significance claim (the
pre-registered binomial threshold was computed for n=33; a fair test at
n=7 would need its own, much higher, critical value, and 7 trials can't
clear a directional test at any reasonable α regardless). **This is
neither a clean pass nor a clean fail of the pre-registered prediction —
it's a finding that the test itself needs the taxonomy-coverage problem
fixed before it can run cleanly.**

This connects directly to Phase B, not just Phase A: `RelevanceScorer`
and `SkillsScorer` share the same underlying `SkillMatcher`/taxonomy, so
the fallback hybrid recommended for JD-match mode in Phase B (seed
primary, ESCO t=0.55 fallback) would very likely raise the number of
seed-taxonomy zero-skill JDs from 20/33 toward the same coverage Phase A
measured for the hybrid (33/33) — which would make this contrast test
actually runnable on the full corpus, not just 7 resumes. **Re-run this
test after Phase B lands, before drawing any conclusion about whether
relevance's flat regression is range restriction or a broken proxy** — the
current run can't distinguish those with only 7 informative trials.

**Scheduling correction**: C1 was scoped as independent of A and B — it
isn't, because `RelevanceScorer` and `SkillsScorer` share a matcher. This
result is now downstream of Phase B, not parallel to it. **Next cycle is
Phase B, then C re-run against the hybrid** — not C run again on its own.

**A second bug, distinct from coverage, found in the same result**:
`score_resume` returning 0.00 for a JD with zero recognizable skills is
*scoring what it can't assess* — the same failure class bug-2's
uncomputable guard was built for (`check_quantification`, see earlier),
now found in relevance. A JD that genuinely contains no seed/ESCO-
recognizable skill is a case with nothing to compare against, not a case
where the resume failed to match anything — those are different claims,
and the current code can't tell them apart. This survives Phase B's
coverage fix, not just predates it: even after the hybrid drops the
zero-skill-JD count from 20/33 toward ~0, whatever residual JDs still
yield nothing (real postings occasionally do — a one-line internal
transfer posting, for instance) should return `uncomputable`, not a
confident, resume-independent 0.00 that a naive report would read as "no
match" rather than "nothing to grade." **Build this guard alongside Phase
B's wiring, not as a follow-up discovery** — it's the same shape of fix,
in the same code path, found while that path was already open.

## Phase B: wired, and Phase C1 re-run against it

**Shipped**: `services/skills/hybrid_matcher.py` (`HybridSkillMatcher`,
seed primary / ESCO t=0.55 fallback, drop-in for `SkillMatcher` wherever
one is expected) and the `score_resume` uncomputable guard
(`services/scoring.py`, `ScoreResult.score: int | None`), both with real
tests (`tests/test_hybrid_matcher.py`, `tests/test_scoring.py` updated) —
243/243 passing.

**Configuration, not a branch in SkillsScorer, as required**: the
seed-vs-ESCO decision lives in `HybridSkillMatcher.for_jd(...)`, called
once per JD by whoever assembles the matcher for a `run_analysis` call —
`SkillsScorer` and `RelevanceScorer` are unchanged and don't know or care
which matcher they were handed. No-JD mode keeps using a plain
`SkillMatcher` (seed only); nothing routes it through the hybrid. A third
mode, or a future extractor (ojd-daps-skills, if the numpy blocker
clears), is a different `for_jd`-equivalent factory, not a scorer edit.

**A real bug caught by reading the code before shipping, not by hitting
it**: `score_resume` calls `matcher.taxonomy.get(skill_id)` to name a
"missing" skill (required by the JD, never found in the resume) — a case
that's common, not rare. `HybridSkillMatcher` had no `.taxonomy` and would
have crashed on the first missing-ESCO-skill case. Fixed with
`_EscoTaxonomyProxy`, tested (`TestTaxonomyProxy`) before it ever ran
against real data.

**The both-layers-empty path**: not present in any of the 33 real JDs
(ESCO at t=0.55 covers all 20 of seed's zero-skill JDs, at whole-document
granularity) — tested synthetically, as instructed
(`TestBothLayersEmpty`), confirming `score_resume` returns `score=None`,
not a crash and not a false 0, when neither layer finds anything.

**A related, real instance found in the field, not synthetic**: R20 (not
one of the 20 seed-zero JDs) still produced `score=None`. Traced: whole-
document seed extraction finds "excel" (`HybridSkillMatcher.for_jd`
therefore decides seed succeeded, no fallback), but `_requirement_weights`
— the actual chunk-level, boilerplate-filtered weight computation
`score_resume` uses — finds that "excel" only inside a chunk classified
`BOILERPLATE` ("Position Qualifications: Bachelor's degree in
Mechanical..."), which carries zero weight and is skipped entirely. Net:
seed contributes nothing usable, but `for_jd`'s coarser whole-document
check never saw that and didn't trigger the ESCO fallback either. The
uncomputable guard caught the resulting `total==0` correctly regardless —
this is the guard doing exactly its job, not a failure of it. But it's a
real, precise refinement worth logging, not silently absorbed: **`for_jd`'s
fallback decision and `_requirement_weights`'s actual weight computation
use different bases** (whole-document unfiltered vs. chunk-level
boilerplate-filtered) and can disagree, always in the same direction (a
JD that should fall back to ESCO doesn't). Follow-up: base `for_jd`'s
decision on whether `_requirement_weights` itself would return a nonzero
total, not on a separate whole-document pre-check — not fixed this cycle,
logged so R20's specific case isn't the only place this is known.

### Phase C1 re-run

Same pre-registered criterion, same threshold (≥10/33), same random seed
(20260830) — not renegotiated. Now via `HybridSkillMatcher.for_jd(...)`
in production code, not the ad-hoc benchmark script's logic.

**Wins: 20/33, p≈0.0000 — PASS.** But the number that actually matters
here is how much cleaner the evidence is, not the win count itself:

| | first run (seed only) | re-run (hybrid) |
|---|---|---|
| structurally uncomputable/zero | 26/33 (contaminated) | 1/33 (R20, a real edge case, not contamination) |
| genuinely nonzero true score | 7/33 | **18/33** |
| genuine zero true score (real "no overlap," not structural) | 0 (couldn't distinguish) | 14/33 |
| win rate on genuinely-informative cases | 5/7 (71%) | **12/18 (67%)** |

ESCO fallback triggered on 107/198 candidate scorings (54%) — confirms
the hybrid is doing real work across most of the corpus, not an edge
case. The 18-nonzero-case win rate (67%, n=18) is now the number worth
trusting — more than double the sample size of the first run's only-
somewhat-trustworthy 7, and none of it riding on the coverage-lottery
contamination that made the first run's headline number meaningless.

**Methodological note, not re-litigating the pre-registered verdict**:
R20's uncomputable case was counted as an automatic loss (`-inf`, per the
script's literal pre-registered logic) rather than dropped from the
denominator. That's an implicit imputation, inconsistent with this
project's own "drop the pair, don't impute" rule applied everywhere else
— worth flagging rather than let stand unremarked, even though it doesn't
change the verdict either way: 20/32 (dropped) clears the same threshold
as 20/33 just as clearly.

**What this does NOT yet answer**: the pre-registered prediction was that
relevance might pass the contrast test *while still correlating weakly
with human labels in the regression sense* (range restriction, not a
broken proxy). The contrast test now passes cleanly. Whether the
regression correlation (ρ vs. human "relevance" label) improves under the
hybrid, or stays flat, has NOT been re-measured this cycle — that's the
other half of the prediction, still open. Re-run `compare_taxonomies.py`
or an equivalent against the hybrid before concluding anything about
range restriction vs. a broken proxy.

## Closing the two open threads before Phase D

### The invisible for_jd/`_requirement_weights` disagreement: checked, not more than R20

For each of the 13 clean JDs where seed succeeds at whole-document level
(the ones `for_jd` does NOT fall back on): compared `for_jd`'s basis
(`seed.extract(whole_jd_text).skill_ids`) against `_requirement_weights`'s
actual basis (chunk-level, boilerplate-filtered). **12 of the 13 match
exactly — zero loss.** R20 is the only case with any disagreement at all,
and its disagreement is total (all skills lost), which the uncomputable
guard already catches visibly (`score=None`). **Zero instances of the
concerning case** — a partial loss producing a low-but-plausible score
instead of a `None`. The `for_jd`/`_requirement_weights` basis mismatch
stays a logged, precise follow-up (see the Phase B section above); it does
not move up the queue, because on this corpus it has exactly one visible
consequence and zero invisible ones.

### ρ re-measurement (`scripts/relevance_regression_recheck.py`): range restriction, confirmed

The other half of Phase C1's pre-registered prediction, now answered:

| | n | ρ | p | r² |
|---|---|---|---|---|
| seed only | 12 | +0.135 | 0.675 | 0.009 |
| **hybrid** | **32** | **+0.196** | **0.283** | **0.032** |

Coverage nearly triples (12→32, R20 excluded on both as uncomputable) and
the point estimate moves in the right direction, but **stays weak and not
significant either way** — squarely inside the historical 0.089–0.232
band, not breaking out of it. Combined with the contrast test result
(20/33 pass, 18/33 genuinely informative at 67% win rate): **relevance
discriminates a matched JD from a random one decisively, while still
correlating only weakly with human judgment's finer gradations.** This is
exactly the range-restriction pattern pre-registered as a real
possibility, not the "broken proxy" alternative. Per that pre-
registration: this points at a scaling/threshold problem in how
`score_resume`'s weighted-coverage ratio maps onto the rubric's 0–15
scale, not at rewriting the underlying matching mechanism. Both halves of
the Phase C1 prediction are now closed.

**Scoped out: the embeddings rewrite for relevance (originally Phase C2 —
`sentence-transformers`, section-wise similarity scoring).** Not deferred
for lack of time; ruled out by measurement. The failure mode an
embeddings rewrite would fix is "the proxy can't tell whether a resume
matches its JD" — and the contrast test shows the opposite: it already
discriminates a true match from a random one decisively (20/33, 18/33
genuinely informative, 67% win rate) using nothing but weighted lexical
skill coverage. What's actually weak is fine-grained ranking within the
"plausible match" band, which is a scaling/threshold problem in how a
coverage ratio maps onto a 0–15 point scale — an embedding model would
inherit the identical mapping problem, not fix it. This is the kind of
finding that's easy to lose track of later ("why didn't we just use
embeddings for relevance?") if it isn't written down with the evidence
attached — "I measured that I didn't need it" is a stronger, and more
easily forgotten, answer than "I didn't get to it."

## Phase D: annotation diagnostic (before any parsing code, as instructed)

### R28, checked first — the premise was wrong, and the actual finding is more useful

R28 was carried as "font-encoding corrupt" (ExperienceScorer's docstring:
"its whole document collapses under one garbled heading"). Checked
directly with `pymupdf`'s plain `page.get_text()` before writing any
annotation-handling code: **the text layer is not corrupt at all.**
pymupdf recovers a completely clean extraction — real Experience heading,
real company names, real bullets, no garbling anywhere. The current
column-aware parser's actual failure: `"Experience PUTNAM ASSOCIATES
BURLINGTON, MA"` — the section heading merged onto one line with the
first job entry's company and location, no newline between them. That's
5 words, so it fails the chunker's ≤4-word heading-shape gate and is
never recognized as a heading at all — the entire Experience section
(genuinely detailed, real bullets) falls back to whatever section
preceded it. Same family as the merge artifacts found earlier in the
corpus (e.g. "Front-End) San Francisco, CA"), but here it swallows a
section boundary, not just one line — much higher-impact.

**R28 isn't "unparseable, maybe recoverable via annotations"** — no
annotations are involved in its failure at all. But the natural next
guess — "pymupdf is generally better, prefer it as a fallback" — turned
out to be wrong too, checked before acting on it (see the divergence
sweep immediately below). R28's actual fix is narrow and chunking-layer:
the heading-shape gate, not the extractor.

### Corpus-wide divergence sweep (`scripts/extractor_divergence_diff.py`): checked, and it reverses the obvious read

R28 was found by checking one resume. Swept all 39 against pymupdf before
writing any parser code, per instruction. Two signals, because a raw line-
count diff is dominated by something expected and not a bug: the current
parser intentionally rejoins PDF line-wraps into single logical bullets
("Migrated the primary datastore..." across two physical lines becomes
one), so it has structurally fewer lines than pymupdf's raw per-line
output on *every* resume — 34/39 "flag" on line-count ratio alone, which
is mostly this, not evidence of anything wrong. The whitespace-normalized
character-similarity ratio (immune to line-wrap differences) is the real
signal: **12/39 show genuine low similarity (<0.85)** — R01, R03, R10,
R11, R12, R13, R15, R18, R32, R35, R36, R39. R28 is NOT among them
(0.991) — its bug is structural (one missing newline), not a content
difference, and this metric can't see it.

**Checked 4 of the 12 directly (R10, R11, R12, R35) before concluding
anything about direction — and in all four, pymupdf is the one that's
wrong, not the current parser.** R12: pymupdf's plain extraction produces
"SUMMARY" immediately followed by "Languages: English, French,
Mandarin... Certifications:... Awards/Activities:..." — content from a
different part of the résumé, interleaved in the wrong order; the current
parser's column-aware output is coherent (name → title → contact →
SUMMARY → correct body text). R35: pymupdf produces "EDUCATION" directly
followed by a list of software tool names ("Rhino 3D, Autodesk Maya,
AutoCAD...") and a project name, all scrambled together — the current
parser correctly separates EDUCATION from the SOFTWARE/SKILLS section
that follows it. R11: pymupdf's extraction is missing the name, contact
line, and section heading entirely from the start of the document (they
surface elsewhere, out of order). R10: pymupdf's "PROFILE" heading ends
up positioned after body text that belongs to a different section, with
EDUCATION appearing after degree details that should follow it, not
precede it. **This is exactly the column-scrambling bug the column-aware
extractor was built to fix** (per its own commit: "Add column-aware PDF
extraction, replacing content-stream-order text extraction") — these four
confirm it's still doing necessary, correct work, not confirm a general
pymupdf-is-better pattern.

**So the divergence count (12/39) is real, but the direction is not
"prefer pymupdf" — on every case actually checked, it's the reverse.**
R28 remains a narrow, single-resume, chunking-layer bug (the heading-shape
gate), not evidence the extraction layer needs to change, and not
evidence pymupdf should become a fallback anywhere in this corpus based
on what's been checked so far. The 8 of the 12 not yet individually
checked (R01, R03, R13, R15, R18, R32, R36, R39) are logged as open —
worth a look before treating "current parser wins on multi-column
layouts" as a closed generalization rather than a strong four-case
pattern — but the instruction that mattered ("this may change what the
parser needs to do") is answered: **it doesn't.** The heading-prefix fix
below is the right next step, not an extraction-layer change.

### The heading-prefix fix: shipped

`chunking.py`'s `_split_heading_prefix`, wired into `chunk_document`
alongside `_is_heading` — not a wider word limit (would accept "Skills
include Python, Docker, and Kubernetes" as a heading outright, wrong in
the opposite direction), but the fix specified: detect a known section
term as a PREFIX of an otherwise-too-long line, and split it off when the
remainder looks like a new entity (starts uppercase — a company name, not
a grammatical continuation) rather than classify the whole line. Same
segmentation-vs-classification separation as the earlier topic-token fix,
applied one level down: to where a boundary sits *within* a line, not
just whether one exists on it.

**A real regression caught before shipping, not after**: the first sweep
across all 39 produced 9 hits, 8 of them false positives — "Languages:
English & Spanish fluency", "Skills: Rhino3D, Adobe Illustrator..." — a
fact-listing label matched the same vocab-prefix + capitalized-remainder
test R28 needed. Fixed with a colon guard (a label ends in ":", R28's
merge doesn't) plus an explicit exclusion for "languages" specifically
(one more hit, no colon this time — "LANGUAGES Mandarin (fluent) Spanish
(intermediate)" sitting between two other Skills-adjacent sub-labels —
every occurrence of this word through this mechanism on the real corpus
was a sub-label, never a genuine section, so excluded on that evidence).
Re-swept after both fixes: **1/39, R28 only.** Also swept the held-out
`test_corpus/`: zero hits, zero false positives. 4 new tests
(`tests/test_chunking.py`), 247/247 passing corpus-wide.

**Confirmed end-to-end**: `ExperienceScorer` on R28 goes from
`uncomputable` (score=None) to **18.9/20, scored, 7 real entries, 92.9%
completeness** — close to the human label (16/20), not a silent gap
anymore. R28 was the eval corpus's only covered-set uncomputable case on
this dimension; that's now closed.

**Also corrected**: three places (`services/analysis/scorers.py` ×2,
`tests/test_experience_extraction.py`) that recorded R28 as "a real PDF
extraction failure... font-encoding corruption" — offered as evidence the
uncomputable guard fires on genuine parse failures, not just synthetic
ones. That evidence still stands (the guard did fire correctly, on a real
case), but the reason recorded next to it was wrong, and reads as a
strong result until checked. Fixed in place, not just noted here.

### The annotation diagnostic itself: real, and larger than a corner case

Across all 39, using `pymupdf`: **12/39 PDFs (31%) carry at least one URI
annotation, and all 12 have at least one link entirely absent from the
text layer** — not a sometimes-problem, a whenever-links-exist problem on
this corpus. R36 is the clearest case: 10 URI annotations (YouTube videos,
GitHub, Gumroad, two article links), all 10 invisible to the current
text-layer parser. The partial cases (R16, R19, R38: 1/3 links missing)
are consistently the `mailto:` link — an icon or styled contact line
whose visible text doesn't literally contain the address the link target
does. Confirms Phase D's premise directly, on this corpus, before any
parsing code was written: `page.get_links()` + `page.get_text("words")`
(to recover the label under each link's rect) is real, addressable work,
not a speculative one.

**Superseded by the shipped implementation below**: the "12/12 all
affected" framing above was measuring literal-URL-substring presence
(pymupdf diagnostic script), a cruder test than "is there any visible
caption near this link at all". The real, precise numbers are in the next
section — most of these 12 turn out to have real nearby captions ("500
stars on GitHub"), just not the literal URL text. Left in place above
rather than deleted, as a record of what the diagnostic-stage number
claimed before the actual mechanism was built and checked against it.

## Phase D shipped: three-channel parser, `services/parsing/pdf_extract.py`

`.text_layer` (unchanged — what `.text` always returned), `.annotations`
(from `pdfplumber`'s own `page.hyperlinks`, already a dependency — no new
one needed for this), `.merged` (text plus a recovered listing of links
the text layer alone can't surface). Two findings, both real properties
on `ExtractionResult`, not just diagnostic script output:

- **`unclickable_urls`**: a URL/email written as visible text with no
  backing annotation. Confirmed on 5/12 annotation-carrying resumes (R04,
  R05, R19, R20, R36) — typed contact info that isn't actually clickable
  in the PDF itself, not just invisible to a parser.
- **`invisible_annotations`**: a link with literally no text-layer words
  under its rect — an icon with zero caption. **Only 1/12** (R01, two
  `mailto:` icon links) once measured precisely via bounding-box overlap,
  not literal-URL matching. The other 11 (R36 included) have real nearby
  captions ("500 stars on GitHub") that a reader — and now this parser's
  `.merged` channel via the label, and `check_completeness` below via the
  raw annotation URI — can use even without the literal URL text. The
  original 12/12 framing overstated this specific finding; the corrected,
  smaller number is still real and still worth having.

**A genuine pre-existing bug found as a byproduct, out of scope to fix at
the source**: `pdfplumber`'s own word extraction duplicates every
character ~17x for one font-quirky caption on R36 ("harshibar" →
"hhhh...aaaa..."), and this leaks into the plain `.text` channel too (126
such runs measured in R36's extracted text, not just the one caption
checked). Not something this module's column/reading-order logic
introduces — checked directly. Collapsed via `_collapse_repeated_chars`
for THIS module's label-matching specifically (needed for correctness
here); the core `.text` channel is left as-is, since changing it needs
its own investigation (why does pdfplumber's glyph clustering duplicate
characters for this font) and its own verification pass against every
downstream scorer that already consumes `.text` — logged here so it isn't
lost, not fixed in a two-line patch.

**Correction, found by testing against a real (not synthetic) resume**:
the first version of `_collapse_repeated_chars` collapsed ANY run of 4+
identical characters anywhere in a string. Run against a real user's
résumé (`evaluation/manual/`, gitignored — real PII, not committed), it
turned `anumishra555555@gmail.com` (a real Gmail address with six genuine
repeated digits) into `anumishra5@gmail.com` — a different, wrong email
address, and the `mailto:` annotation's own target no longer matched its
own displayed label as a result. Not a resume defect; a bug in this
module's own "fix" for R36's corruption, caught by testing on real
external data the synthetic corpus never exercised. Fixed by requiring
both a longer minimum run (8+, not 4+) and that such runs cover more than
half the string before treating it as R36-style whole-word duplication —
R36's actual corruption duplicates every character of a word uniformly
(≈17x each, comfortably clear of this bar); an isolated legitimate repeat
inside otherwise-normal text (a repeated-digit email, a `555.555.5555`
phone placeholder — both now covered by regression tests) never gets
close. 2 new tests, re-verified clean against the real resume after the
fix (`mailto:` target now matches its label exactly).

11 new tests (`tests/test_pdf_annotations.py`), all offline (synthetic
`Word`/`LinkAnnotation` construction, not real PDFs, for the pure-logic
pieces — real-PDF behavior verified directly against R01/R36/R04/R19/R20
above).

## Phase E shipped: contact & link verification, `services/verification/contact_links.py`

Own section, own report (`ContactLinkReport.summary` — "Contact & Links:
N issues found"), not folded into the structure score, per the brief:
verified facts (does this domain accept mail, is this a dialable number)
shouldn't be averaged in with a rubric's estimated judgments.

- **Phone** (`phonenumbers`): valid vs. possible-but-not-real (this eval
  corpus's own `555.555.5555` placeholder convention is a live, correctly-
  flagged example — a reserved/fictional NANP range, not a real number).
  The `"0091"`-instead-of-`"+91"` case from the brief: detected, and the
  corrected number reports `is_valid=True` (it's real) but still
  `has_issue=True` (the raw text was still malformed as typed) — a real
  bug in the first version of this logic, caught by this module's own
  tests before it shipped: the early-return path on a successful
  correction silently dropped the flag.
- **Email** (`email-validator`, MX lookup): syntax vs. deliverability are
  now two different exception types (`EmailSyntaxError` /
  `EmailUndeliverableError`), not one — a second bug this module's own
  tests caught: catching the shared base class reported Canva's dead
  template domain (`hello@reallygreatsite.com`, confirmed against this
  eval corpus directly — fails deliverability, real network check, not
  assumed) as a *syntax* error, which it isn't. Also checked, not
  assumed: `check_deliverability=True` does NOT reliably catch a
  plausible-typo domain that still has mail service configured
  (`gmial.com` passes) — it catches dead/placeholder domains specifically,
  a narrower claim than "catches typos".
- **Links** (async `httpx`, concurrent via `asyncio.gather` — sequential
  would take up to 80s on R36's 10 links at an 8s timeout each, gathered
  is bounded by the slowest single check): `ok | unreachable | blocked`,
  never a bare "invalid". LinkedIn's own profile pages return 405 to a
  plain HEAD request, confirmed directly against a real profile URL, not
  assumed from the brief — classified `blocked`, not `unreachable`.
  Platform shape rules (LinkedIn needs `/in/<username>`, GitHub needs a
  username/repo, not the bare homepage) are narrow on purpose: flag a
  clearly-wrong shape, not every URL variation.
- **Completeness**: name/phone/email/location always; LinkedIn generally;
  portfolio/GitHub only for fields the brief names (technical/design).
  Checks annotation URIs alongside visible text, not just text — R36's
  real case again: "500 stars on GitHub" captions a link with no literal
  "github.com" in the text at all; a text-only check flagged a resume
  with substantial real GitHub content as missing it entirely, fixed once
  found by checking the actual link targets already available from Phase
  D's `.annotations`. Name detection also corrected mid-build: this
  corpus's several single-name aliases ("Harshibar") were flagged missing
  by a name-shaped regex that required 2+ words; narrowed to the first 2
  lines specifically (not widened blindly) so a bare capitalized word
  doesn't also match a section heading a few lines down.

24 new tests (`tests/test_contact_links.py`): 18 offline (fast suite),
6 marked `slow` (real MX lookups and HTTP HEAD requests, this project's
existing convention for network-dependent tests — not a new marker).
Dependencies added to `requirements.txt`, pinned:
`phonenumbers`, `email-validator`, `dnspython`, `httpx`, `tldextract`.

**Not yet done**: wiring either module into a live route (`/v2/analyze`,
Phase G) or the `Scorer` protocol — both exist as real, tested,
standalone modules, callable end-to-end (verified against R36/R05/R01
above), not yet connected to a request path. Full suite: 276 passed, 7
deselected (`slow` — 6 new network tests plus 1 pre-existing).

## Phase G: cover letter fix + finish wiring

Diagnosed before touching anything, per the request: `/api/resume/
cover-letter` was wired end-to-end (not a "never connected" case) and
failed for exactly one reason, confirmed live rather than assumed —
`GEMINI_API_KEY` unset, `cover_letter.py`'s raw `requests.post()` sent
`?key=None`, Gemini returned a clean 400 `API_KEY_INVALID`, and the route
turned that into a generic 500. Alongside that: no timeout (the same class
of bug already fixed once this session in `analyzer.py`'s `check_grammar`),
no missing-key guard, manual markdown-fence-stripping + `json.loads()`
instead of Gemini's actual structured-output mode, and `requests` used
directly but never declared in `requirements.txt` (present only because
something else pulled it in transitively).

**Fix, not a rebuild**, per the diagnosis:

- **`services/llm/client.py`** (new): the shared Gemini client the two
  existing call sites (`check_grammar`, `generate_cover_letter`) both
  needed and had each independently half-built — key resolution, a
  client-side timeout, `generate_json()` using
  `response_mime_type="application/json"` + `response_schema` (a plain
  JSON-Schema dict; the SDK uppercases `type` internally — confirmed
  against the installed `google-generativeai==0.8.6`'s
  `GenerationConfig.response_schema: protos.Schema | Mapping[str, Any] |
  type`, not assumed), and one exception type (`LLMError`) so a caller
  gets a single thing to catch regardless of *why* the call failed. Drops
  `requests` entirely rather than declaring it — one HTTP path through the
  codebase (the SDK), not two, and nothing to add to `requirements.txt`
  for a dependency that got in by accident.
  `services/interview.py` has the identical duplicated pattern (SDK-based,
  same manual fence-stripping, no timeout, no key guard) and was **not**
  touched here — flagged, not fixed, since it wasn't part of this pass's
  scope; it's the third occurrence this module exists to prevent a fourth
  of.
- **`services/llm/prompts.py`** + `services/llm/prompts/*.txt`: prompt
  text moved out of inline f-strings into template files
  (`grammar_check.txt`, `cover_letter.txt`), loaded via `load_prompt(name,
  **kwargs).format(**kwargs)`. Both templates dropped the old "return ONLY
  this JSON" instruction and literal JSON example — enforcing shape is
  `response_schema`'s job now, not prompt text asking nicely.
- **`services/cover_letter.py`** (rewritten): calls the shared client,
  raises `CoverLetterError` (never a bare `Exception`) on failure. Kept
  deliberately separate from `services/analysis/` and the eval harness —
  generative, unevaluated, no rubric, no labels, and it never will have
  either; see the README's Measurement section. Does **not** adopt
  `services/analysis/models.py`'s three-status/JD-optional model — a
  cover letter without a JD is a generic template, not a weaker-but-usable
  artifact the way a no-JD *score* still is, so the JD stays hard-required
  and a request without one is refused with 422, not answered with
  something weak.
- **`routes/resume.py`**: `/cover-letter` returns 422 (missing
  resume_text/job_description, with the JD case explaining *why* it's
  required) or 502 (`CoverLetterError` — generation failed upstream), never
  a bare 500 with Gemini's raw response text leaking through.

**Phase G wiring, same pass**: `POST /api/resume/v2/analyze` (new route,
`/analyze` v1 left untouched) accepts an uploaded PDF directly rather than
pre-extracted text, so it can use channels `/analyze` never had access to:
`extract_document(...).merged` (three-channel parser, Phase D) feeds
`services.analysis.run_analysis` (six-dimension rubric, three-status
model, JD optional — quality mode without one, match mode with), and
`extract_document(...).annotations` feeds
`services.verification.contact_links.build_report` (Phase E) for real
phone/email/link verification alongside the score. Both modules were
"built and tested but standalone" before this; now connected to a request
path, verified against a real fixture end-to-end (`canva_style.pdf`):
correct mode selection, every dimension carrying a status, a real MX
lookup correctly failing `priya.sharma@example.com`'s placeholder
`example.com` domain. One pre-existing minor false-positive noticed while
verifying, not touched (out of scope for this pass, module already shipped
as tested): `extract_phone_candidates`'s regex matches a bare date range
like "2022-2026" as a phone candidate.

**CI gate** (closes item 1, "Regression gate (`make eval` + CI)", above):
`tests/test_v2_analyze_regression_gate.py` extends the
`test_structure_regression_gate.py` pattern from one dimension to the
whole dual-mode pipeline — coverage and mean signed gap, gated with real
margin above/around freshly measured baselines (quality mode: 27/39
coverage, MAE 12.85, gap −2.59; match mode: 27/39 coverage, MAE 17.36, gap
−8.74 — both meaningfully conservative relative to human labels, which
this gate protects against getting *worse*, not a claim that they're
good). Deliberately excludes Spearman ρ from the gate, per this file's own
repeated finding that ρ is too unstable at this sample size to be a
contract (quality-mode ρ=0.260, p=0.11 — not even significant). Also added
`.github/workflows/tests.yml`, since none existed — a gate test nobody
runs automatically isn't a gate; it now runs the full fast suite on every
push/PR to `main`.

**README**: rewritten (was UTF-16, and described the pre-Phase-0 v1-only
architecture as if it were the whole system) with an explicit Measurement
& Evaluation section — what's measured (the six rubric dimensions,
calibrated against the 39-resume corpus, coverage reported alongside
accuracy, ρ excluded from the CI gate for the reason above) and what isn't
and never will be (cover letter and interview generation — "generative,
unevaluated" stated outright, not left for a reader to assume the same
measurement discipline covers them).

27 new tests across four files (`test_llm_client.py`, `test_cover_letter.py`,
`test_v2_analyze_route.py`, `test_v2_analyze_regression_gate.py` — the
last of those runs against the real 39-PDF corpus, same as the structure
gate). Full suite: 305 passed, 7 deselected (`slow`).

**Deferred, unchanged from before this pass**: relevance scaling fix,
LLM-judge comparison (per the original Phase G scope, after the UI if time
is short), and `services/interview.py`'s migration onto the shared LLM
client (flagged above, not part of this pass).

## Phase G loose ends

### 1. What accounts for quality-mode MAE 15.9 → 12.85, gap → −2.59

The CI gate now enforces these numbers, so where they came from needs to be
traceable, not asserted. It isn't one number moving smoothly — it's two
different measurements stitched together, and the trace below keeps them
apart on purpose.

**The 15.9 doesn't belong on the same line as 12.85.** It comes from
`evaluation/metrics_report.md`, committed once (`3a05e6e`, before
`resume_eval_dual_mode.py` existed) and never regenerated. Read closely,
its own "blended" figure is scale-corrected MAE=15.89 on n=38 (R31 dropped
as a duplicate), produced by a *different* script (`resume_eval_report.py`)
comparing a manually /80-to/100-rescaled machine score — from a version of
the pipeline where ExperienceScorer didn't exist yet ("experience
UNCOMPUTABLE -- ATSync has no scorer for experience" is printed directly
in that report) — against the human's raw total/100, *including* the ~15-20
relevance points the machine could never contribute to even after the
rescale. That's not this gate's methodology at all. The true first
measurement using *today's* methodology (`resume_eval_dual_mode.py`,
machine's self-renormalizing `AnalysisResult.score` vs. human
`(total-relevance)/85*100`, n=39, no rows dropped) is commit `f148d18`,
where it was built: **MAE=18.14, mean signed gap=−16.57, coverage=26/39**.
That's the real starting line. Re-measured directly by checking out each
commit since in a scratch worktree and re-running the unmodified script
against the unmodified 39-resume corpus — not estimated from memory:

| commit | change | MAE | gap | coverage |
|---|---|---|---|---|
| `f148d18` | dual-mode methodology's first measurement | 18.14 | −16.57 | 26/39 |
| `9f9a3f2` | Writing scorer rewrite (Item 4) | 11.19 | −6.72 | 26/39 |
| `d15edfe` | Structure regression gate (no scoring change) | 11.19 | −6.72 | 26/39 |
| `e76f997` | Achievements: qualitative-impact partial credit | 10.78 | −6.26 | 26/39 |
| `bf9f6e6` | Achievements: ceiling fix | 10.50 | −5.93 | 26/39 |
| `20a4b80` | ExperienceScorer built (Phase 1 item 1) | 13.34 | −3.24 | 26/39 |
| `7bfaba0` | fact-listing fix reach verified | 13.26 | −3.01 | 26/39 |
| `4c65c38` | ESCO comparison (measured, not swapped) | 13.26 | −3.01 | 26/39 |
| `0dee840`, `8cdb875` | JD corpus rebuild (JD-side; quality mode has no JD) | 13.26 | −3.01 | 26/39 |
| *(uncommitted, this session, pre-Phase-G)* | chunking.py `_split_heading_prefix` | **12.85** | **−2.59** | **27/39** |

Named contributors, largest first:

- **Writing scorer rewrite** (`9f9a3f2`) is the single largest contributor
  by a wide margin — MAE fell 7 points and the gap closed by two-thirds in
  one commit. Consistent with the scorer's own docstring: the old
  word-repetition proxy was blind to passive voice and filler entirely: a
  defect-injection test proved it, not a correlation number alone.
- **ExperienceScorer's introduction** (`20a4b80`) is the one genuinely
  non-monotonic step, and worth naming as its own finding, not glossed
  over: it moved the *gap* sharply toward zero (−5.93 → −3.24, the closest
  any single commit gets to unbiased) while making *MAE worse*
  (10.50 → 13.34). Both are real and both are explained by the same fact:
  Experience is weak-but-real signal on its own (rho≈0.21-0.23 against the
  human "experience" column, p≈0.16-0.20 — not significant, reported as
  such in `ExperienceScorer`'s own docstring), so adding a 20-point
  dimension with high per-resume variance shrinks the *average* bias
  while adding noise to *individual* estimates. A gate on gap direction
  alone would have called this a pure win; MAE catches what it misses —
  exactly why both are gated, not just one.
- **Achievements fixes** (`e76f997`, `bf9f6e6`) contributed a combined
  ~0.7 points of MAE and ~0.8 of gap — real, modest, not the headline.
- **The uncommitted `_split_heading_prefix` fix** (chunking.py, Phase D —
  see `_split_heading_prefix`'s own docstring for the full mechanism)
  accounts for the final step to 12.85/−2.59/27, by closing R28's
  previously-uncomputable Experience (and, since it's a chunker-level
  section-boundary fix, potentially Structure/Writing/Achievements) gap.
  This is the one entry in the table not reachable from `git log` alone —
  it predates this session's Phase G work but was never committed; it's
  the same fix `test_structure_regression_gate.py`'s docstring already
  cites (MAE 2.49→2.41, gap −0.74→−0.67 on Structure specifically). Flagged
  here as still-uncommitted so it doesn't stay untraceable — see "Still
  open" below.
- **`d15edfe`, `4c65c38`, `0dee840`, `8cdb875` moved nothing** — confirmed,
  not assumed: `d15edfe` only added the structure gate test, `4c65c38`
  measured the ESCO taxonomy and explicitly chose not to swap it,
  `0dee840`/`8cdb875` rebuilt the JD corpus, which quality mode (no JD)
  structurally cannot be touched by.

**No denominator change.** Checked specifically, since the gate depends on
it:
- **n is 39 at every single row in the table above** — `resume_eval_dual_mode.py`
  computes MAE/gap over all 39 rows regardless of per-resume completeness;
  coverage is a separate count, never folded into the accuracy figure (the
  same coverage-beside-accuracy discipline this whole file keeps repeating).
- **The comparison basis (`(total-relevance)/85*100` on the human side,
  `AnalysisResult.score`'s available-points renormalization on the machine
  side) has not changed once** since `AnalysisResult`/`DimensionResult`
  were introduced (`7b3ad75`) — `git log 7b3ad75..HEAD` and the current
  uncommitted diff both show zero touches to `models.py` or `pipeline.py`.
  `available_points` itself does shift per-resume when a dimension flips
  uncomputable→scored (R28 gaining Experience's 20 points, here) — that's
  the renormalization mechanism working as designed (see `AnalysisResult`'s
  own docstring), not a moving goalpost.
- **`evaluation/labels.csv` and `backend/data/skills_seed.json`** (ground
  truth and taxonomy) have been unchanged since before `f148d18` even
  existed (last touched at `3a05e6e` and `6f01875` respectively) — checked
  via `git log`, not assumed.
- **`scoring.py`'s and `scorers.py`'s uncommitted diffs are match-mode-only**
  (a `score_resume`/`RelevanceScorer` uncomputable guard for a JD with zero
  weighted requirements) or docstring-only (a corrected explanation of
  R28's original root cause, no behavior change) — checked line by line;
  neither touches anything quality mode calls.
- **`pdf_extract.py`'s uncommitted diff doesn't touch the `.text` scoring
  path at all** — `_collapse_repeated_chars` (the R36 fix) is called only
  from `_label_for_link`, for link-annotation label matching, never from
  the reading-order/`.text` extraction `resume_eval_dual_mode.py` actually
  scores against. Confirmed by tracing every call site, not assumed from
  the fix's description.

**Still open**: the `_split_heading_prefix` fix (chunking.py) and its
downstream effects on `scorers.py`/`scoring.py` docstrings remain
uncommitted as of this entry — they predate this session's Phase G work
and are real, tested (`test_structure_regression_gate.py` already gates on
Structure's post-fix numbers), but committing them is separate housekeeping
from this loose-end log, not done here.

### 2. `services/interview.py` timeout guard

Flagged in the Phase G entry above as the third occurrence of the pattern
that started this whole effort (`GEMINI_API_KEY` unset → an LLM call that
can never succeed → no timeout to bound how long it hangs trying anyway).
Fixed: `generate_interview_questions` now passes
`request_options={"timeout": ...}` to `generate_content`, same guard
`check_grammar` and `generate_cover_letter` already have via
`services/llm/client.py`. Not migrated onto the shared client itself in
this pass — see `routes/resume.py`'s `/interview-questions` handler, which
already catches any exception (including a timeout) and returns 500; a
full migration would also mean adopting `LLMError` and structured output,
a larger, separate change from a five-line guard against the specific hang
risk named here.

### 3. Coverage in the README

`evaluation/backlog.md` is where the measurement history and its caveats
live in full, but coverage — how often `/v2/analyze` actually produces a
complete score — belongs next to the accuracy numbers in the README too,
not filed only here where a reader evaluating the tool is unlikely to
look. Added to the README's Measurement & Evaluation section: quality mode
27/39 (69%), match mode 27/39 (69%), stated beside the MAE/gap figures
instead of asserting accuracy alone.
