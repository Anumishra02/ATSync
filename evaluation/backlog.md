# ATSync scoring — evaluation backlog

Source of truth for what the 39-resume eval (`evaluation/labels.csv` vs
`evaluation/predictions.csv`, computed by `backend/scripts/resume_eval_*.py`)
found, and what it means to do about it. Numbers below are from the harness
after the bug-3 (heading segmentation/vocab) and bug-2 (uncomputable
quantification) fixes landed; bug-1 (hyphen-truncated bullets) is still
unpatched, on purpose (see its entry).

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
