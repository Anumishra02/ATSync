
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from services.parser import extract_text_from_pdf
from services.scoring import legacy_ats_score
from services.interview import generate_interview_questions
from services.analyzer import full_analysis
from services.cover_letter import generate_cover_letter
from services.matching.chunking import normalize_document_text
from services.skills.matcher import SkillMatcher
from services.skills.taxonomy import Taxonomy

router = APIRouter()

# Built once at import, not per request -- the taxonomy index gets rebuilt
# on every SkillMatcher() construction, which is a visible per-request cost
# at ESCO's 13.9k-skill scale.
_SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "skills_seed.json"
_matcher = SkillMatcher(Taxonomy.from_seed_json(_SEED_PATH))


# ── Request models ────────────────────────────────────────────────────────────

class ATSRequest(BaseModel):
    resume_text: str
    job_description: str

class InterviewRequest(BaseModel):
    resume_text: str
    job_description: str

class FullAnalysisRequest(BaseModel):
    resume_text: str
    job_description: str
    filename: str
    file_size: int

class CoverLetterRequest(BaseModel):
    resume_text: str
    job_description: str
    tone: str = "professional"


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    file_bytes = await file.read()
    text = extract_text_from_pdf(file_bytes)

    if not text:
        raise HTTPException(status_code=400, detail="Could not extract text from PDF")

    return {
        "filename": file.filename,
        "characters": len(text),
        "preview": text[:500],
        "full_text": text,
    }


@router.post("/score")
def score_resume(request: ATSRequest):
    if not request.resume_text or not request.job_description:
        raise HTTPException(status_code=400, detail="Both resume text and job description required")

    result = legacy_ats_score(
        _matcher,
        normalize_document_text(request.resume_text),
        normalize_document_text(request.job_description),
    )
    return result


@router.post("/interview-questions")
def get_interview_questions(request: InterviewRequest):
    if not request.resume_text or not request.job_description:
        raise HTTPException(status_code=400, detail="Both fields required")

    try:
        result = generate_interview_questions(request.resume_text, request.job_description)
        return result
    except Exception as e:
        print(f"[interview] ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
def analyze_resume(request: FullAnalysisRequest):
    resume_text = normalize_document_text(request.resume_text)
    job_description = normalize_document_text(request.job_description)
    ats = legacy_ats_score(_matcher, resume_text, job_description)
    result = full_analysis(
        resume_text,
        request.filename,
        request.file_size,
        job_description,
        ats,
    )
    return result


@router.post("/cover-letter")
def get_cover_letter(request: CoverLetterRequest):
    if not request.resume_text or not request.job_description:
        raise HTTPException(status_code=400, detail="Both fields required")
    try:
        result = generate_cover_letter(
            request.resume_text,
            request.job_description,
            request.tone
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))