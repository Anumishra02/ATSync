from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from services.parser import extract_text_from_pdf
from services.ats_scorer import calculate_ats_score
from services.interview import generate_interview_questions
from services.analyzer import full_analysis

from services.cover_letter import generate_cover_letter
router = APIRouter()

class ATSRequest(BaseModel):
    resume_text: str
    job_description: str

class InterviewRequest(BaseModel):
    resume_text: str
    job_description: str

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
        "full_text": text
    }

@router.post("/score")
def score_resume(request: ATSRequest):
    if not request.resume_text or not request.job_description:
        raise HTTPException(status_code=400, detail="Both resume text and job description required")

    result = calculate_ats_score(request.resume_text, request.job_description)
    return result

@router.post("/interview-questions")
def get_interview_questions(request: InterviewRequest):
    if not request.resume_text or not request.job_description:
        raise HTTPException(status_code=400, detail="Both fields required")
    
    try:
        result = generate_interview_questions(request.resume_text, request.job_description)
        return result
    except Exception as e:
        print(f"ERROR in interview questions: {str(e)}")  # shows in terminal
        raise HTTPException(status_code=500, detail=str(e))
    


class FullAnalysisRequest(BaseModel):
    resume_text: str
    job_description: str
    filename: str
    file_size: int

@router.post("/analyze")
def analyze_resume(request: FullAnalysisRequest):
    from services.ats_scorer import calculate_ats_score
    ats = calculate_ats_score(request.resume_text, request.job_description)
    result = full_analysis(
        request.resume_text,
        request.filename,
        request.file_size,
        request.job_description,
        ats
    )
    return result

class CoverLetterRequest(BaseModel):
    resume_text: str
    job_description: str
    tone: str = "professional"

@router.post("/cover-letter")
def get_cover_letter(request: CoverLetterRequest):
    if not request.resume_text or not request.job_description:
        raise HTTPException(status_code=400, detail="Both fields required")
    result = generate_cover_letter(
        request.resume_text,
        request.job_description,
        request.tone
    )
    return result