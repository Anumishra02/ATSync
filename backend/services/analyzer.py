import re
import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

from services.matching.chunking import ChunkKind, SKILLS_SECTION_NAMES, chunk_resume, normalize_document_text
from services.scoring import EXPECTED_SECTIONS
from services.scoring import check_sections as _heading_based_sections

load_dotenv()
_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=_GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# check_grammar's fallback when the LLM can't be reached -- reused by both
# the missing-key early return and the request-failure except branch so the
# two paths can't silently drift into different shapes.
_GRAMMAR_FALLBACK = {
    "score": 85,
    "mistakes": [],
    "issues": 0,
    "verdict": "Could not analyze",
    "tip": "Proofread your resume carefully"
}

# Grammar checking makes a network call per resume. Without a key it will
# never succeed, so skip the request instead of paying (and risking a hang
# on) a call that's certain to fail. With a key, a short client-side timeout
# still bounds the call -- a stalled network shouldn't be able to hang
# /analyze indefinitely either.
_GRAMMAR_TIMEOUT_SECONDS = 10

_SECTION_DISPLAY_NAMES = {
    "experience": "Experience",
    "education": "Education",
    "skills": "Skills",
    "projects": "Projects",
    "certifications": "Certifications",
}

def check_quantification(text: str) -> dict:
    """Quantified-achievement rate among real bullets.

    Used to find bullets with its own regex (`r'[•\\-\\*]\\s*(.+)'`) straight
    over the raw text. That regex treats ANY hyphen as a bullet marker, not
    just a leading one -- so a mid-word hyphen ("Full-stack", "Front-End",
    "code-splitting", "Real-Time") fabricates a phantom bullet out of a
    Summary/title/skills line, or truncates a real bullet's wrapped
    continuation into a fresh one. Concretely, on one resume in the eval
    corpus this dragged a bullet count from 14 real achievement bullets to
    23 "bullets" (7 fabricated fragments, all counted as unquantified), and
    swung the quantification score from a true 50% down to a reported 30%.

    Sourcing bullets from chunk_resume instead fixes this for free: its
    _BULLET regex is anchored to the start of a line, so mid-word hyphens
    can't create or truncate anything. Skills-section bullets ("Python",
    "Docker") are additionally excluded -- a tech-stack list can't be
    "quantified" and shouldn't be judged on this axis; including them was a
    second, separate source of denominator inflation.

    Precondition: `text` is already normalized (chunk_resume's own
    precondition -- see chunking.py's module docstring). Callers already
    normalize once at the API boundary; this does not re-normalize.

    Returns score=None -- uncomputable, not 0 -- when the resume has no
    real bulleted content to assess at all: a prose-paragraph resume (no
    glyph bullets anywhere), or one whose bullet glyph the chunker doesn't
    recognize. A confident 0% claims "graded, and failed"; the honest
    answer for a resume this check structurally cannot read is "nothing to
    grade." See full_analysis for how a None sub-score is handled when
    blending into overall_score.
    """
    chunks = chunk_resume(text)
    bullets = [
        c for c in chunks
        if c.kind is ChunkKind.BULLET and c.section not in SKILLS_SECTION_NAMES
    ]
    if not bullets:
        return {
            "score": None,
            "total_bullets": 0,
            "quantified": 0,
            "issues": 0,
            "verdict": "No bulleted achievements found -- quantification can't be assessed",
            "tip": "Add numbers to your bullet points (e.g. 'Improved performance by 30%')"
        }
    quantified = [c for c in bullets if re.search(r'\d+', c.text)]
    score = round(len(quantified) / len(bullets) * 100)
    return {
        "score": score,
        "total_bullets": len(bullets),
        "quantified": len(quantified),
        "issues": len(bullets) - len(quantified),
        "verdict": "Good" if score >= 60 else "Needs improvement",
        "tip": "Add numbers to your bullet points (e.g. 'Improved performance by 30%')"
    }

def check_repetition(text: str) -> dict:
    words = re.findall(r'\b[a-zA-Z]{5,}\b', text.lower())
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    repeated = {w: c for w, c in freq.items() if c >= 4 and w not in [
        'experience', 'project', 'using', 'based', 'working', 'developed',
        'built', 'implemented', 'managed', 'created', 'designed'
    ]}
    top = sorted(repeated.items(), key=lambda x: -x[1])[:5]
    issues = len(top)
    return {
        "score": max(0, 100 - issues * 15),
        "issues": issues,
        "repeated_words": [{"word": w, "count": c} for w, c in top],
        "verdict": "Good" if issues == 0 else f"{issues} repeated words found",
        "tip": "Vary your language — avoid repeating the same words too often"
    }

def check_contact_info(text: str) -> dict:
    has_email = bool(re.search(r'\b[\w.-]+@[\w.-]+\.\w+\b', text))
    has_phone = bool(re.search(r'[\+\d][\d\s\-\(\)]{8,}', text))
    has_linkedin = bool(re.search(r'linkedin\.com|linkedin:', text, re.I))
    has_github = bool(re.search(r'github\.com|github:', text, re.I))
    score = sum([has_email, has_phone, has_linkedin, has_github]) * 25
    return {
        "score": score,
        "email": has_email,
        "phone": has_phone,
        "linkedin": has_linkedin,
        "github": has_github,
        "issues": 4 - sum([has_email, has_phone, has_linkedin, has_github]),
        "verdict": "Complete" if score == 100 else "Missing some contact info",
        "tip": "Include email, phone, LinkedIn and GitHub for best results"
    }

def check_file_format(filename: str, file_size_bytes: int) -> dict:
    is_pdf = filename.lower().endswith('.pdf')
    size_mb = round(file_size_bytes / (1024 * 1024), 2)
    size_ok = size_mb < 2
    score = (50 if is_pdf else 0) + (50 if size_ok else 0)
    return {
        "score": score,
        "is_pdf": is_pdf,
        "size_mb": size_mb,
        "size_ok": size_ok,
        "issues": (0 if is_pdf else 1) + (0 if size_ok else 1),
        "verdict": "Good" if score == 100 else "Issues found",
        "tip": "Use PDF format and keep file size under 2MB"
    }

def check_sections(text: str) -> dict:
    """Section presence, from actual resume headings.

    Used to regex-match the whole body for words like "developed" and
    "work" -- so almost every resume passed almost every check regardless
    of whether it had that section (see services/scoring.py's docstring for
    the original finding). Now reads only lines the chunker classified as
    headings. Return shape is unchanged so callers (full_analysis, the
    frontend's SectionsSection) don't need to change.
    """
    chunks = chunk_resume(normalize_document_text(text))
    found_map = _heading_based_sections(chunks)
    sections = {
        _SECTION_DISPLAY_NAMES[key]: found_map.get(key, False)
        for key in EXPECTED_SECTIONS
    }
    found = sum(sections.values())
    score = round(found / len(sections) * 100)
    return {
        "score": score,
        "sections": sections,
        "found": found,
        "total": len(sections),
        "issues": len(sections) - found,
        "verdict": "Good" if score >= 80 else "Missing important sections",
        "tip": "Include Education, Experience, Skills, Projects sections"
    }

def check_grammar(text: str) -> dict:
    if not _GEMINI_API_KEY:
        # No key configured -- every call would fail anyway. Skip straight
        # to the same fallback the except branch below returns, instead of
        # making (and waiting on) a request that can't succeed.
        return dict(_GRAMMAR_FALLBACK)

    prompt = f"""
Analyze this resume text for spelling and grammar mistakes.
Return ONLY valid JSON, no markdown, no extra text:
{{
  "mistakes": [
    {{"word": "misspelled_word", "suggestion": "correct_word", "context": "sentence containing it"}}
  ],
  "score": 0-100,
  "verdict": "short verdict"
}}
Find up to 5 real mistakes only. If no mistakes found, return empty mistakes array and score 100.
Resume text:
{text[:2000]}
"""
    try:
        response = model.generate_content(
            prompt, request_options={"timeout": _GRAMMAR_TIMEOUT_SECONDS}
        )
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        result = json.loads(raw)
        result["issues"] = len(result.get("mistakes", []))
        result["tip"] = "Fix spelling and grammar errors for a professional impression"
        return result
    except Exception:
        return dict(_GRAMMAR_FALLBACK)

def full_analysis(resume_text: str, filename: str, file_size: int, job_description: str, ats_data: dict) -> dict:
    quantification = check_quantification(resume_text)
    repetition = check_repetition(resume_text)
    contact = check_contact_info(resume_text)
    file_fmt = check_file_format(filename, file_size)
    sections = check_sections(resume_text)
    grammar = check_grammar(resume_text)

    # A component score of None means that check couldn't be run at all
    # (currently only quantification, when a resume has no real bulleted
    # content -- see check_quantification). Treating None as 0 would punish
    # a resume for a check that was inapplicable to it; dropping the term
    # without renormalizing would silently shrink the achievable max below
    # 100 for exactly those resumes. Redistribute the missing weight
    # proportionally across whatever DID run instead, so overall_score
    # stays comparable on the same 0-100 scale regardless of which checks
    # fired.
    weighted_components = [
        (ats_data.get("ats_score", 0), 0.3),
        (quantification["score"], 0.15),
        (repetition["score"], 0.1),
        (contact["score"], 0.1),
        (file_fmt["score"], 0.1),
        (sections["score"], 0.15),
        (grammar["score"], 0.1),
    ]
    usable = [(score, weight) for score, weight in weighted_components if score is not None]
    weight_used = sum(weight for _, weight in usable)
    overall = round(sum(score * weight for score, weight in usable) / weight_used) if weight_used else 0

    total_issues = (
        quantification["issues"] +
        repetition["issues"] +
        contact["issues"] +
        file_fmt["issues"] +
        sections["issues"] +
        grammar["issues"]
    )

    return {
        "overall_score": overall,
        "total_issues": total_issues,
        "categories": {
            "ats_match": {
                "score": ats_data.get("ats_score", 0),
                "matched": ats_data.get("matched_skills", []),
                "missing": ats_data.get("missing_skills", []),
                "issues": ats_data.get("total_jd_skills", 0) - ats_data.get("total_matched", 0),
                "verdict": ats_data.get("verdict", ""),
                "tip": "Add missing skills to your resume to improve ATS match"
            },
            "quantification": quantification,
            "repetition": repetition,
            "contact": contact,
            "file_format": file_fmt,
            "sections": sections,
            "grammar": grammar,
        }
    }