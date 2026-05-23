import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("models/gemini-2.0-flash")

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


# import google.generativeai as genai
# import os
# import json
# import re
# from dotenv import load_dotenv

# # Use explicit path so it works regardless of where uvicorn is launched from
# load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

# api_key = os.getenv("GEMINI_API_KEY")
# if not api_key:
#     raise ValueError("GEMINI_API_KEY not found — check your .env file")

# genai.configure(api_key=api_key)

# # gemini-1.5-flash is stable and widely available across all API tiers
# model = genai.GenerativeModel("gemini-1.5-flash")
# model = genai.GenerativeModel("models/gemini-2.0-flash")


# def generate_cover_letter(resume_text: str, job_description: str, tone: str = "professional") -> dict:
#     prompt = f"""
# You are an expert career coach and professional writer.

# Generate a compelling cover letter based on this resume and job description.

# RESUME:
# {resume_text}

# JOB DESCRIPTION:
# {job_description}

# TONE: {tone}

# Return ONLY valid JSON with no markdown fences, no extra text, nothing before or after the JSON object:
# {{
#     "cover_letter": "full cover letter text here with proper paragraphs separated by \\n\\n",
#     "subject_line": "Email subject line for this application",
#     "key_points": ["point1", "point2", "point3"],
#     "word_count": 250
# }}

# Rules:
# - Cover letter should be 250-300 words
# - 4 paragraphs: opening hook, relevant experience, why this company, call to action
# - Be specific to THIS candidate's actual experience — no generic filler
# - Tone should be {tone}
# - Opening line must NOT start with "I am writing to apply for..."
# - Return ONLY the raw JSON object, nothing else
# """
#     try:
#         response = model.generate_content(prompt)
#         raw = response.text.strip()

#         # Robustly strip markdown code fences if present
#         raw = re.sub(r"^```(?:json)?\s*", "", raw)
#         raw = re.sub(r"\s*```$", "", raw)
#         raw = raw.strip()

#         data = json.loads(raw)

#         # Validate expected keys are present
#         return {
#             "cover_letter": data.get("cover_letter", ""),
#             "subject_line": data.get("subject_line", ""),
#             "key_points": data.get("key_points", []),
#             "word_count": data.get("word_count", len(data.get("cover_letter", "").split())),
#         }

#     except json.JSONDecodeError as e:
#         print(f"[cover_letter] JSON parse error: {e}")
#         print(f"[cover_letter] Raw response was:\n{raw}")
#         raise

#     except Exception as e:
#         print(f"[cover_letter] Unexpected error: {type(e).__name__}: {e}")
#         raise
