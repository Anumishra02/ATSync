import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

def generate_interview_questions(resume_text: str, job_description: str) -> dict:

    prompt = f"""
You are a senior technical interviewer at a top product company.

Given this candidate's resume and job description, generate interview questions.

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}

Generate exactly this JSON structure (no extra text, no markdown, no code blocks):
{{
    "technical_questions": [
        {{"question": "...", "topic": "...", "difficulty": "easy/medium/hard"}}
    ],
    "project_questions": [
        {{"question": "...", "project": "..."}}
    ],
    "behavioral_questions": [
        {{"question": "...", "competency": "..."}}
    ],
    "tips": ["tip1", "tip2", "tip3"]
}}

Generate 4 technical, 3 project-based, 3 behavioral questions.
Be very specific to THIS candidate's actual resume. Not generic questions.
Return only raw JSON, nothing else.
"""

    response = model.generate_content(prompt)

    raw = response.text.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)