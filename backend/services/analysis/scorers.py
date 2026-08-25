"""The six scoring dimensions.

Structure and Achievements wrap existing (tested) logic unchanged -- see
evaluation/backlog.md, which found no reason to touch their internals.
Three dimensions ARE built differently than the live route currently
computes them, each because the backlog identified why the old
computation carries no signal:

  Relevance   Uses score_resume (weighted by JD emphasis, evidence-linked)
              instead of legacy_ats_score's keyword_score. The backlog's
              regression found keyword_score's plain word-overlap
              uncorrelated with human relevance judgment (r^2=0.018,
              p=0.71) -- "no concept of what a human means by relevant."
              score_resume already exists and is tested; it just wasn't
              wired into anything live yet.
  Writing     Rewritten from pure word-repetition (see WritingScorer's
              own docstring) after a defect-injection test proved that
              proxy blind to passive voice and filler entirely.
  Experience  Structured extraction against the rubric's own mechanical
              definition (org, title, city/state, dates per entry, plus
              reverse-chronological order) -- see experience.py and
              ExperienceScorer's docstring. Replaces a first-pass
              bullet-volume placeholder that existed only because no
              rubric-shaped implementation had been built yet.

Skills keeps legacy_ats_score's skill_score-style computation (flat
match-rate, not emphasis-weighted) specifically so it stays a different
signal from Relevance rather than a duplicate of it under another name --
Skills answers "did the resume name the right skills," Relevance answers
"how strongly does the resume align with what this JD actually
emphasizes."

Max points (relevance 15, skills 15, experience 20, achievements 20,
writing 15, structure 15 -- summing to 100) match Resume-Scores-39.xlsx's
"Rubric & Notes" sheet exactly, not the illustrative numbers from the
Phase 0 discussion, so machine dimension scores stay comparable to the 39
human labels already collected.
"""

from __future__ import annotations

import re
from typing import Protocol

from wordfreq import zipf_frequency

from services.analyzer import check_quantification
from services.analysis.experience import extract_all_experience_entries
from services.matching.chunking import ChunkKind, FACT_LISTING_PATTERN, chunk_job_description, chunk_resume
from services.scoring import check_sections, score_resume
from services.skills.matcher import SkillMatcher

from .models import DimensionResult


class Scorer(Protocol):
    name: str
    max_points: float
    requires_jd: bool

    def score(self, resume_text: str, jd_text: str | None, matcher: SkillMatcher) -> DimensionResult: ...


class StructureScorer:
    """Section-heading presence -- see services/scoring.py's check_sections."""

    name = "structure"
    max_points = 15.0
    requires_jd = False

    def score(self, resume_text: str, jd_text: str | None, matcher: SkillMatcher) -> DimensionResult:
        chunks = chunk_resume(resume_text)
        sections = check_sections(chunks)
        found, total = sum(sections.values()), len(sections)
        pct = found / total if total else 0.0
        return DimensionResult(
            dimension=self.name,
            score=round(pct * self.max_points, 1),
            max_points=self.max_points,
            status="scored",
            detail={"sections": sections},
        )


_FILLER_PHRASES = (
    "basically", "sort of", "kind of", "helped with", "worked on",
    "responsible for", "was involved in", "in order to", "literally",
    "various things", "a lot of", "things related to", "helping to",
    "in charge of", "duties included",
)
# Passive voice: "was/were/is/are/been/being" + a past-participle-shaped
# word ("built", "written", "given", ...). Deliberately crude (a shape
# heuristic, not real POS tagging) -- consistent with this project's other
# regex-based checks (see check_quantification's docstring on why a cheap,
# inspectable heuristic beats an opaque one here), and good enough to
# distinguish "Built a service" from "A service was built by me".
_PASSIVE_PATTERN = re.compile(r"\b(?:was|were|is|are|been|being)\s+\w+(?:ed|en)\b", re.IGNORECASE)

# Contact/header lines: an email, a URL, or a line naming 2+ of the
# standard profile-link domains. Excluded from writing analysis entirely
# (not just from the repetition count) -- passive-voice/filler detection
# make no sense against a contact line either, and it's simpler to filter
# once than to special-case three different checks against the same line.
_CONTACT_LINE_PATTERN = re.compile(
    r"@|https?://|linkedin\.com|github\.com|\.(?:com|io|dev|me|net)\b", re.IGNORECASE
)

# Same stoplist check_repetition already used, so this isn't a behavior
# change on the non-skill-aware part of the fix. Kept as a cheap fallback
# alongside the zipf check below, same relationship as COMMON_WORDS to
# wordfreq in services/skills/taxonomy.py.
_WRITING_STOPWORDS = frozenset({
    "experience", "project", "using", "based", "working", "developed",
    "built", "implemented", "managed", "created", "designed",
})
# A word this common in general English naturally recurs 4+ times in any
# resume of ordinary length ("which", "different", "department",
# "students", "system" all score 5.0+) -- that's a property of the English
# language, not a stylistic defect. Repeating a genuinely distinctive word
# ("leveraged", "spearheaded", or a technical term outside the taxonomy
# like "opencv", zipf 1.62) is a real signal; repeating "which" is not.
# Threshold picked to clear every common-word false positive the
# defect-injection test surfaced while still catching genuinely rare-word
# repetition -- same mechanism as the skill matcher's fuzzy-tier wordfreq
# gate (services/skills/matcher.py), reused here for an analogous problem.
_WRITING_COMMON_WORD_ZIPF_THRESHOLD = 4.0


class WritingScorer:
    """Repetition (skill- and common-word-aware) + passive voice +
    filler-phrase density, scoped to bullet content.

    Rewritten from a pure word-repetition proxy after the defect-injection
    test (test_writing_discrimination.py) proved that proxy blind to
    passive voice and filler entirely -- three synthetic resumes with
    heavily passive or filler-laden bullets scored identically to the
    clean baseline (15.0/15.0, all three), which is exactly the "carries
    no reliable signal" finding backlog.md's regression already flagged
    (r^2=0.016, p=0.73). Per that item's own instruction: the proxy
    needed rewriting, not recalibrating.

    Also fixes backlog.md item 4's named bug, and two broader versions of
    it the defect-injection test surfaced empirically, not by inspection:
    repetition no longer penalizes a word that's part of a skill the
    matcher recognized (e.g. "Python" appearing 4+ times in a genuinely
    Python-heavy resume), a word that's simply common in general English
    (the penalty was saturating on words like "which"/"department" that
    have nothing to do with writing quality -- injecting MORE repetition
    into a resume that already had many such words was invisible until
    this was fixed), or a word that's the résumé owner's own name/handle
    repeating across contact links ("github.com/harshibar",
    "linkedin.com/in/harshibar") -- also not a writing-quality signal.

    Still an honest limitation, not resolved by any of the above: measured
    against the 39 human labels after every fix above, correlation is
    essentially zero (rho=-0.04, p=0.81, n=39) -- better than the -0.19
    a single missing fix (contact-line exclusion) produced, but nowhere
    near evidence the proxy tracks human writing judgment. One real,
    concrete case why: R11 (human writing=7/15, middling) scores a
    perfect 15.0/15.0 here -- zero repeated words, zero passive lines,
    zero filler lines detected, and yet a human found something worth
    marking down. Passive voice, filler phrases, and word repetition are
    real writing problems, but they are evidently not the ones this rater
    weighted, or not the form they take in this corpus. The
    defect-injection suite proves this proxy responds to the three
    specific things it was built to detect (40/40, real degradations, not
    assumed) -- it does not prove those three things are what "good
    writing" means to a human reader. Closing that gap likely needs a
    genuinely different kind of signal (grammar/clarity assessment,
    plausibly the deferred check_grammar/Gemini path, or real POS-based
    analysis), not a fourth regex heuristic bolted onto these three.

    Phase 1 item 1 follow-up: after fixing the exact same category-error
    denominator bug in AchievementsScorer (fact-listing lines like
    "Coursework: ..." counted as ungraded content they structurally can't
    satisfy), checked whether the same bug was present here -- it was, on
    mechanism grounds (a fact-listing line isn't prose a human would ever
    judge for passive voice or filler either), so it's excluded here too
    (see FACT_LISTING_PATTERN). Measured, not assumed, whether it actually
    mattered: only 6/39 corpus resumes changed score at all, and real
    correlation moved from rho=-0.040 (p=0.81) to rho=-0.011 (p=0.95) --
    both indistinguishable from zero, the difference is noise at this
    sample size. Applied anyway, because it's correct on mechanism grounds
    independent of whether it moves the correlation number, and this IS
    the confirming result: unlike Achievements (where the same fix moved
    slope, intercept, r^2, and rho together -- a mechanical bug with a
    mechanical fix), nothing here moves, because there's no mechanical bug
    left to find. Writing's gap and Experience's gap (see
    ExperienceScorer's docstring) are the same kind of finding: a scorer
    built faithfully to what's mechanically checkable, correlating weakly
    with a human rater who was evidently judging something else. See
    evaluation/backlog.md's "Construct validity" section for the
    consolidated writeup.
    """

    name = "writing"
    max_points = 15.0
    requires_jd = False

    def score(self, resume_text: str, jd_text: str | None, matcher: SkillMatcher) -> DimensionResult:
        # Scored over any scorable content (bullets AND prose, excluding
        # headings/boilerplate) -- NOT bullets only. A prose-paragraph
        # resume can exhibit passive voice, filler, and repetition just as
        # validly as a bulleted one; restricting to bullets would make
        # Writing uncomputable on exactly the resumes Achievements already
        # is (see AchievementsScorer), unnecessarily stacking two
        # uncomputable dimensions where only one is actually warranted.
        # Contact/header lines ("github.com/harshibar | linkedin.com/in/harshibar")
        # aren't prose and shouldn't be judged as writing at all -- found via
        # the defect-injection test's real-corpus correlation check: a
        # résumé owner's own name or handle repeating across contact links
        # was flagging as "repetition," penalizing writing quality for
        # something with nothing to do with how the résumé is written.
        # A "Coursework: X, Y, Z" fact-listing line is the same category
        # error, for the same reason it was excluded from Achievements'
        # denominator -- see FACT_LISTING_PATTERN and this class's own
        # docstring for what checking this actually changed.
        lines = [
            c.text for c in chunk_resume(resume_text)
            if c.is_scorable
            and not _CONTACT_LINE_PATTERN.search(c.text)
            and not FACT_LISTING_PATTERN.match(c.text.lstrip())
        ]
        if not lines:
            return DimensionResult(
                dimension=self.name, score=None, max_points=self.max_points, status="uncomputable",
                detail={"reason": "no scorable content (bullets or prose) to assess"},
            )

        skill_words = {
            w.lower()
            for m in matcher.extract(resume_text).matches
            for w in m.surface.split()
        }
        words = re.findall(r"\b[a-zA-Z]{5,}\b", " ".join(lines).lower())
        freq: dict[str, int] = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1
        repeated = {
            w: c for w, c in freq.items()
            if c >= 4
            and w not in _WRITING_STOPWORDS
            and w not in skill_words
            and zipf_frequency(w, "en") < _WRITING_COMMON_WORD_ZIPF_THRESHOLD
        }

        passive_lines = sum(1 for line in lines if _PASSIVE_PATTERN.search(line))
        passive_rate = passive_lines / len(lines)

        filler_lines = sum(
            1 for line in lines if any(phrase in line.lower() for phrase in _FILLER_PHRASES)
        )
        filler_rate = filler_lines / len(lines)

        raw = 100.0
        raw -= min(len(repeated), 5) * 15  # same per-word penalty check_repetition used
        raw -= passive_rate * 40
        raw -= filler_rate * 40
        raw = max(0.0, raw)

        pct = raw / 100.0
        return DimensionResult(
            dimension=self.name,
            score=round(pct * self.max_points, 1),
            max_points=self.max_points,
            status="scored",
            detail={
                "repeated_words": sorted(repeated),
                "passive_line_rate": round(passive_rate, 2),
                "filler_line_rate": round(filler_rate, 2),
            },
        )


class AchievementsScorer:
    """Quantified-bullet rate -- see analyzer.check_quantification.

    Already returns score=None (uncomputable) for a resume with no real
    bulleted content -- that maps directly onto this model's status field.

    Phase 1 item 3 ("Achievements calibration"): the diagnosis handed down
    was slope=0.79, r^2=0.71, large negative intercept on n=9 -- i.e. real
    signal, but a resume with SOME quantification still scored near zero
    because the old mechanism gave literal zero credit to any bullet
    lacking a digit, no matter how strong its impact language. Re-measured
    on the full 39-resume corpus (n=27 with both a human achievements score
    and a computable machine one) before touching anything: slope=0.571,
    intercept=-2.33, r^2=0.439, mean_signed_gap=-30.59 (machine badly
    underscoring relative to human, on the 0-100 check_quantification
    scale). The two largest-gap resumes (R22: human=90, machine=33: R24:
    human=50, machine=0) were both cases of a bullet with undeniable impact
    but no literal number -- "Streamlined investment review process
    firmwide, resulting in improved financial and risk analysis",
    "Spearheaded integration of people, processes, and systems between two
    teams" -- being treated identically to "Attended meetings".

    Fix: check_quantification now gives partial (0.5x) credit to a bullet
    that contains qualitative impact language (a curated marker list --
    "led", "spearheaded", "streamlined", "increased", "resulting in", etc.)
    but no digit, instead of zero. A real number is still worth strictly
    more than qualitative language alone (see
    test_qualitative_credit_is_never_worth_more_than_a_real_number) -- this
    is partial credit, not equivalence. Re-measured after the fix:
    slope=0.580, intercept=-0.10, r^2=0.519.

    Correction on how to read that: slope=0.580 with intercept~=0 is not
    "an offset plus a mystery residual" -- it's pure scale compression. A
    human score of H predicts a machine score of 0.58*H; the -27.81 mean
    gap is just what that slope implies at the corpus's mean human score,
    not a separate unexplained defect. The near-zero intercept is exactly
    the signature of a correct mechanism fix (see the intercept move from
    -2.33 there), so the qualitative-credit fix is real and done. What was
    left after it is that the scorer's reachable ceiling was well under
    100%: checked directly, the highest machine ratio across all 39
    resumes was 0.69, on a resume humans scored 0.90-0.95. Root cause
    (checked before touching anything, per the same discipline as above):
    the bullet denominator included fact-listing lines -- "Coursework:
    Machine Learning, Data Structures...", "Languages: Written and spoken
    fluency in Spanish..." -- that were never achievement claims and can't
    carry a number by construction, structurally identical to the
    Skills-section bullets already excluded but living under Education or
    "Additional Information" instead. See _FACT_LISTING_PATTERN.
    Re-measured after excluding those: slope=0.701, intercept=-0.06,
    r^2=0.577, Spearman rho=0.764 (up from 0.730) -- both the linear fit
    and the rank correlation improved together, which is the signal this
    captured real structure rather than fitting noise (an arbitrary
    denominator change that was just noise-fitting would trade one for the
    other, not improve both). Ceiling still isn't fully closed (max ratio
    0.72, not 1.0) -- some genuine achievement bullets describe scope or a
    built artifact without a digit or one of the curated impact markers
    ("Built a back-end data service... to log and analyze query
    behavior"), and expanding the marker list to catch them was
    deliberately not done here: generic action verbs ("built", "developed",
    "managed") would blur the qualitative-marker list back into "any bullet
    that describes doing something," which is exactly the undiscriminating
    signal _QUALITATIVE_IMPACT_MARKERS was built to avoid. That's honest
    remaining headroom, not something this change claims to have solved.
    """

    name = "achievements"
    max_points = 20.0
    requires_jd = False

    def score(self, resume_text: str, jd_text: str | None, matcher: SkillMatcher) -> DimensionResult:
        result = check_quantification(resume_text)
        if result["score"] is None:
            return DimensionResult(
                dimension=self.name, score=None, max_points=self.max_points, status="uncomputable",
                detail={"reason": result["verdict"]},
            )
        pct = result["score"] / 100.0
        return DimensionResult(
            dimension=self.name,
            score=round(pct * self.max_points, 1),
            max_points=self.max_points,
            status="scored",
            detail={
                "total_bullets": result["total_bullets"],
                "quantified": result["quantified"],
                "qualitative": result["qualitative"],
            },
        )


# Calibrated against the 39-resume evaluation corpus (evaluation/): recognized
# -skill counts for genuinely strong software/data/ML résumés in that corpus
# (the only fields skills_seed.json's 92-skill taxonomy has real vocabulary
# for) clustered 11-31; 12 sits at the low end of that cluster, so a resume
# needs to be genuinely skill-rich, not just skill-present, to max out.
#
# KNOWN, DOCUMENTED LIMITATION, not silently absorbed: for the ~30 non-tech
# fields in that same corpus (art history, accounting, marketing, ...) this
# scorer reads as near-zero regardless of actual skill quality, because the
# taxonomy has almost no vocabulary for those domains -- the same
# taxonomy-coverage gap the backlog documents on the JD-relevance side (see
# resume_eval_predict.py's taxonomy_covered flag). Growing the taxonomy
# fixes both at once; this scorer isn't a separate bug to chase.
_SKILLS_NO_JD_TARGET_COUNT = 12


class SkillsScorer:
    """Skill-name match rate.

    Dual mode, per the Phase 0 spec: with a JD, "how well do the
    candidate's skills match this job" (flat match-rate against the JD's
    own required skills). Without one, "how many recognized skills does
    this résumé contain at all" (see _SKILLS_NO_JD_TARGET_COUNT for the
    calibration and its documented taxonomy-coverage caveat).

    Deliberately does NOT exclude FACT_LISTING_PATTERN lines the way
    AchievementsScorer and WritingScorer do -- checked, not assumed:
    "Computer skills: Excel, SQL, Python" and "Languages: Spanish" style
    lines are exactly where real skills legitimately get declared, and
    excluding them loses genuine, correctly-recognized skill matches on
    15/39 corpus resumes (some heavily -- R38 alone loses 15). A
    fact-listing line is a category error for achievement/writing
    judgment, which it structurally can't satisfy; it's the opposite for
    skill matching, which is exactly the content it's built to satisfy.
    """

    name = "skills"
    max_points = 15.0
    requires_jd = False  # can run without a JD -- see the table in the Phase 0 spec

    def score(self, resume_text: str, jd_text: str | None, matcher: SkillMatcher) -> DimensionResult:
        resume_skill_ids = matcher.extract(resume_text).skill_ids

        if jd_text is None:
            pct = min(len(resume_skill_ids) / _SKILLS_NO_JD_TARGET_COUNT, 1.0)
            return DimensionResult(
                dimension=self.name,
                score=round(pct * self.max_points, 1),
                max_points=self.max_points,
                status="scored",
                detail={"mode": "count", "skills_found": len(resume_skill_ids)},
            )

        jd_skill_ids = matcher.extract(jd_text).skill_ids
        if not jd_skill_ids:
            # The JD itself named no recognized skills -- not the résumé's
            # fault, and not the same failure as "no résumé content to
            # read" (Achievements' uncomputable case), but equally not a
            # rate you can compute a numerator/denominator for.
            return DimensionResult(
                dimension=self.name, score=None, max_points=self.max_points, status="uncomputable",
                detail={"reason": "JD named no recognized taxonomy skills"},
            )
        matched = jd_skill_ids & resume_skill_ids
        pct = len(matched) / len(jd_skill_ids)
        return DimensionResult(
            dimension=self.name,
            score=round(pct * self.max_points, 1),
            max_points=self.max_points,
            status="scored",
            detail={"mode": "jd_match", "matched": len(matched), "jd_skills": len(jd_skill_ids)},
        )


class RelevanceScorer:
    """JD-alignment, weighted by requirement emphasis (required > preferred).

    Uses score_resume, not legacy_ats_score's keyword_score -- see the
    module docstring for why (backlog.md's regression finding). Always
    requires a JD; that's the dimension's entire reason to exist.
    """

    name = "relevance"
    max_points = 15.0
    requires_jd = True

    def score(self, resume_text: str, jd_text: str | None, matcher: SkillMatcher) -> DimensionResult:
        if jd_text is None:
            return DimensionResult(
                dimension=self.name, score=None, max_points=self.max_points, status="not_applicable",
            )
        result = score_resume(matcher, resume_text, jd_text)
        pct = result.score / 100.0
        return DimensionResult(
            dimension=self.name,
            score=round(pct * self.max_points, 1),
            max_points=self.max_points,
            status="scored",
            detail={"matched": len(result.matched), "missing": len(result.missing)},
        )


# Section membership uses "experience" as a case-insensitive SUBSTRING of
# the chunker's raw section label, not an exact match -- real résumés use
# "Work Experience", "Leadership Experience", "Marketing Experience",
# "Accounting Experience", none of which equal the literal string
# "experience". An exact-match version of this scorer found zero
# experience content on 33 of the 39 resumes; the substring version finds
# content on 38/39 (the one miss, R28, is a real PDF extraction failure
# upstream -- its whole document collapses under one garbled heading,
# "ane oe" -- not a scorer bug; see experience.py's module docstring).
_EXPERIENCE_ORDER_WEIGHT = 0.2  # of max_points; the rest is per-entry completeness


class ExperienceScorer:
    """Org name, job title, city/state, and dates, checked per role entry,
    plus a separate reverse-chronological order check across entries --
    the rubric's own mechanical definition of this dimension, not a
    semantic judgment of the experience's quality (that's Achievements and
    Relevance). See services/analysis/experience.py for the extraction
    itself; this class only turns its output into points.

    Phase 1 item 1. Replaces a first-pass placeholder that scored bullet
    volume (see this class's git history) because no rubric-shaped
    implementation existed yet -- that placeholder never claimed to
    measure the rubric's actual definition, just resume depth as a rough
    stand-in for it.

    Scoring, built deliberately as "points per satisfied criterion" (not
    "average quality across entries capped below 100%") so a genuinely
    complete resume can reach 20/20 -- the same ceiling mistake Phase 1
    item 3 found and fixed in AchievementsScorer is designed out from the
    start here:
      - 80% of max_points: mean, across every real entry, of how many of
        {org, title, location, dates} that entry has. A resume where every
        entry has all four naturally hits 1.0, no matter how many entries
        there are.
      - 20% of max_points: the order check (see
        check_reverse_chronological_order). 1.0 when there's no detected
        violation -- including when there's no comparable pair at all
        (nothing to contradict), so a single-entry resume or one whose
        dates are all unparseable isn't penalized twice for a gap the
        completeness score already counts.

    Uncomputable (not a confident 0) when zero real entries parse from any
    experience-labeled section -- R28 in the eval corpus exercises this:
    its whole document extracts under one garbled heading with no
    "experience" substring anywhere, so there's nothing here to grade.

    Known, honest limitations, not silently absorbed:
      - Title detection is keyword-based only
        (services/analysis/experience.py's _TITLE_KEYWORDS) and will miss
        an uncommon title outside that list. Measured on the 39-resume
        corpus: org 82.7%, title 69.1%, location 59.3%, dates 84.6% of
        entries detected.
      - A resume section that lists honor-society/professional-affiliation
        memberships under an experience-labeled heading without its own
        detected sub-heading (a real corpus case, R05: "PROFESSIONAL
        AFFILIATIONS AND INVOLVEMENT" isn't recognized as a heading by
        chunking.py's vocabulary) gets read as a run of low-completeness
        "entries" -- these aren't jobs and grading them on job-entry
        criteria is a category error the extractor can't currently avoid.
      - Location detection favors "City, ST"/"City, Country" shapes; a
        resume that legitimately omits location for on-campus/remote
        listings (common in the corpus's student resumes: "UCR" with no
        city/state repeated) reads as missing, which is arguably correct
        under a strict reading of the rubric but may not match how a human
        skimmed it.

    Measured against the 39-resume corpus's human "experience" score (n=38,
    R28 uncomputable on both sides): slope=0.237, intercept=12.57,
    r^2=0.069, Spearman rho=0.214 (p=0.20, not significant), MAE=3.59. This
    is real, weak signal -- reported honestly, not hidden. The clearest
    disagreements are informative about WHY: R14 and R10 are both
    Canva-style templates where the experience section's bullets were
    never replaced ("Lorem ipsum dolor sit amet..." -- literal, unfilled
    placeholder text), correctly scored near the bottom by the human
    (4/20, 7/20) but only moderately by this scorer (12/20, 12/20) because
    their headers ARE genuinely well-formed (real-looking org names,
    titles, dates) even though there's nothing behind them. R13 is
    starker: one entry, zero bullets, every header fact present -- 20/20
    here, 8/20 from the human. This scorer is intentionally checking only
    the rubric's stated mechanical fields, not "is there real substance
    behind this entry" -- that's a content-quality question, and it's
    AchievementsScorer's job, not this one's: R14 and R13 both correctly
    come back uncomputable on the achievements dimension (zero bullets to
    grade), so the overall pipeline doesn't end up crediting an empty
    template just because this dimension can't see past its header line.

    This is a construct-validity finding, not a scorer defect, and the
    second one of its shape in this project (WritingScorer's docstring is
    the first) -- see evaluation/backlog.md's "Construct validity"
    section for the consolidated writeup and the decision made about it.
    Short version: the rubric column is titled "depth and relevance of
    roles" but its own stated criteria are all formatting completeness;
    this scorer measures exactly that, faithfully, and a human rater
    evidently judged something closer to the column's name than its
    criteria. The more thorough fix -- split into a `_completeness`
    sub-score (this) and a `_substance` sub-score (semantic, different
    method) -- is real future work, deliberately not done here because it
    changes the rubric's shape mid-flight and breaks comparability with
    the 39 frozen labels. What IS done: report the gap honestly instead
    of tuning this scorer toward the labels, which would make the number
    look better and the project worse.
    """

    name = "experience"
    max_points = 20.0
    requires_jd = False

    def score(self, resume_text: str, jd_text: str | None, matcher: SkillMatcher) -> DimensionResult:
        chunks = chunk_resume(resume_text)
        exp_chunks = [
            c for c in chunks
            if c.kind in (ChunkKind.BULLET, ChunkKind.PROSE) and c.section and "experience" in c.section
        ]
        entries, order_ok, comparable, violations = extract_all_experience_entries(exp_chunks)
        if not entries:
            return DimensionResult(
                dimension=self.name, score=None, max_points=self.max_points, status="uncomputable",
                detail={"reason": "no section containing 'experience' yielded any real entries"},
            )

        fact_counts = [sum(e.facts().values()) for e in entries]
        completeness_pct = sum(fact_counts) / (4 * len(entries))
        order_pct = 1.0 if comparable == 0 else max(0.0, 1 - violations / comparable)
        pct = (1 - _EXPERIENCE_ORDER_WEIGHT) * completeness_pct + _EXPERIENCE_ORDER_WEIGHT * order_pct

        return DimensionResult(
            dimension=self.name,
            score=round(pct * self.max_points, 1),
            max_points=self.max_points,
            status="scored",
            detail={
                "entries": len(entries),
                "completeness_pct": round(completeness_pct, 3),
                "order_ok": order_ok,
                "order_comparable_pairs": comparable,
                "order_violations": violations,
            },
        )


ALL_SCORERS: tuple[Scorer, ...] = (
    StructureScorer(),
    WritingScorer(),
    AchievementsScorer(),
    SkillsScorer(),
    ExperienceScorer(),
    RelevanceScorer(),
)
