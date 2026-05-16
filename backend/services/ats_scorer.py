import re

SKILLS_POOL = [
    "python", "javascript", "c++", "java", "typescript", "sql",
    "node.js", "express.js", "fastapi", "django", "flask",
    "rest api", "restful api", "restful apis",
    "jwt", "authentication", "rbac",
    "react", "next.js", "tailwind", "html", "css",
    "machine learning", "deep learning", "nlp", "xgboost",
    "scikit-learn", "pandas", "numpy", "tensorflow", "pytorch",
    "collaborative filtering",
    "mongodb", "postgresql", "mysql", "redis",
    "docker", "kubernetes", "git", "github", "ci/cd", "aws",
    "data structures", "algorithms", "object-oriented programming",
    "oop", "system design", "problem solving",
    "socket.io", "websockets",
]

SKILL_ALIASES = {
    "restful apis": "rest api",
    "restful api": "rest api",
    "rest apis": "rest api",
    "object oriented programming": "oop",
    "object-oriented programming": "oop",
}

def normalize(text: str) -> str:
    text = text.lower()
    for alias, canonical in SKILL_ALIASES.items():
        text = text.replace(alias, canonical)
    return text

def extract_skills(text: str) -> list[str]:
    text_normalized = normalize(text)
    found = []
    for skill in SKILLS_POOL:
        if skill.lower() in text_normalized:
            if skill not in found:
                found.append(skill)
    return found

def calculate_ats_score(resume_text: str, job_description: str) -> dict:
    resume_normalized = normalize(resume_text)
    jd_normalized = normalize(job_description)

    # Step 1: skills from JD
    jd_skills = extract_skills(jd_normalized)

    # Step 2: check which are in resume
    matched_skills = []
    missing_skills = []
    for skill in jd_skills:
        if skill.lower() in resume_normalized:
            matched_skills.append(skill)
        else:
            missing_skills.append(skill)

    # Step 3: keyword overlap
    jd_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', jd_normalized))
    resume_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', resume_normalized))
    keyword_overlap = jd_words & resume_words
    keyword_score = min(len(keyword_overlap) / max(len(jd_words), 1) * 100, 100)

    # Step 4: skill score
    skill_score = 0
    if jd_skills:
        skill_score = (len(matched_skills) / len(jd_skills)) * 100

    # Step 5: final score
    final_score = round((skill_score * 0.7) + (keyword_score * 0.3), 2)

    # Step 6: verdict
    if final_score >= 80:
        grade = "Excellent"
        verdict = "Strong match! Your resume aligns well with this job."
    elif final_score >= 60:
        grade = "Good"
        verdict = "Decent match. Add missing skills to improve your chances."
    elif final_score >= 40:
        grade = "Average"
        verdict = "Partial match. Significant skill gaps need to be addressed."
    else:
        grade = "Poor"
        verdict = "Weak match. Resume needs major improvements for this role."

    return {
        "ats_score": final_score,
        "grade": grade,
        "verdict": verdict,
        "skill_score": round(skill_score, 2),
        "keyword_score": round(keyword_score, 2),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "total_jd_skills": len(jd_skills),
        "total_matched": len(matched_skills),
        "summary": f"Your resume matched {len(matched_skills)} out of {len(jd_skills)} required skills. "
                   f"Missing: {', '.join(missing_skills) if missing_skills else 'nothing!'}"
    }