import re
import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

def check_quantification(text: str) -> dict:
    bullets = re.findall(r'[•\-\*]\s*(.+)', text)
    quantified = [b for b in bullets if re.search(r'\d+', b)]
    score = round(len(quantified) / max(len(bullets), 1) * 100)
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
    sections = {
        "Education": bool(re.search(r'education|degree|university|college|bachelor|master', text, re.I)),
        "Experience": bool(re.search(r'experience|work|employment|job|intern', text, re.I)),
        "Skills": bool(re.search(r'skills|technologies|tools|languages', text, re.I)),
        "Projects": bool(re.search(r'project|built|developed|created', text, re.I)),
        "Certifications": bool(re.search(r'certif|award|achievement', text, re.I)),
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
        response = model.generate_content(prompt)
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
    except:
        return {
            "score": 85,
            "mistakes": [],
            "issues": 0,
            "verdict": "Could not analyze",
            "tip": "Proofread your resume carefully"
        }

def full_analysis(resume_text: str, filename: str, file_size: int, job_description: str, ats_data: dict) -> dict:
    quantification = check_quantification(resume_text)
    repetition = check_repetition(resume_text)
    contact = check_contact_info(resume_text)
    file_fmt = check_file_format(filename, file_size)
    sections = check_sections(resume_text)
    grammar = check_grammar(resume_text)

    overall = round((
        ats_data.get("ats_score", 0) * 0.3 +
        quantification["score"] * 0.15 +
        repetition["score"] * 0.1 +
        contact["score"] * 0.1 +
        file_fmt["score"] * 0.1 +
        sections["score"] * 0.15 +
        grammar["score"] * 0.1
    ))

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