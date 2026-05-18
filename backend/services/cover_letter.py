import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

def generate_cover_letter(resume_text: str, job_description: str, tone: str = "professional") -> dict:
    prompt = f"""
You are an expert career coach and professional writer.

Generate a compelling cover letter based on this resume and job description.

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}

TONE: {tone}

Return ONLY valid JSON, no markdown, no extra text:
{{
    "cover_letter": "full cover letter text here with proper paragraphs separated by \\n\\n",
    "subject_line": "Email subject line for this application",
    "key_points": ["point1", "point2", "point3"],
    "word_count": 250
}}

Rules:
- Cover letter should be 250-300 words
- 4 paragraphs: opening hook, relevant experience, why this company, call to action
- Be specific to THIS candidate's actual experience — no generic filler
- Tone should be {tone}
- Make the opening line memorable and not "I am writing to apply for..."
Return only raw JSON.
"""
    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        return json.loads(raw)
    except Exception as e:
        return {
            "cover_letter": "Failed to generate. Please try again.",
            "subject_line": "",
            "key_points": [],
            "word_count": 0
        }