
import io
from pathlib import Path

from fastapi import APIRouter, Form, UploadFile, File, HTTPException
from pydantic import BaseModel
from services.analysis.pipeline import run_analysis
from services.parser import extract_text_from_pdf as _legacy_extract_text_from_pdf
from services.parsing.pdf_extract import extract_document
from services.scoring import legacy_ats_score
from services.interview import generate_interview_questions
from services.analyzer import full_analysis
from services.cover_letter import CoverLetterError, generate_cover_letter
from services.matching.chunking import normalize_document_text
from services.skills.matcher import SkillMatcher
from services.skills.taxonomy import Taxonomy
from services.verification.contact_links import build_report

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

    # Column-aware extraction first (fixes the real Canva-scramble bug --
    # see services/parsing/pdf_extract.py). Falls back to the old PyPDF2
    # path on any failure rather than hard-failing the upload -- pdf_extract
    # is well-tested but hasn't seen the full range of real-world PDFs yet,
    # and a worse-but-working extraction beats a 500.
    try:
        result = extract_document(io.BytesIO(file_bytes))
        text = result.text
        parse_status = result.parse_status
        print(
            f"[upload] {file.filename}: pdf_extract "
            f"(columns={result.column_counts}, {result.chars_per_page:.0f} chars/page, "
            f"status={parse_status})"
        )
    except Exception as e:
        print(f"[upload] {file.filename}: pdf_extract failed ({e!r}), falling back to PyPDF2")
        text = _legacy_extract_text_from_pdf(file_bytes)
        # No page count available from the legacy path, so no per-page
        # normalization -- a flat floor is a coarser but still honest
        # safety net for this rarer fallback branch.
        parse_status = "ok" if len(text) >= 50 else "unreadable"

    if parse_status == "unreadable" or not text:
        raise HTTPException(
            status_code=400,
            detail=(
                "This PDF has no extractable text -- it looks like a scanned "
                "image rather than a text-based document. Export or re-save "
                "it as a text PDF (not a scan) and try again."
            ),
        )

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
    if not request.resume_text:
        raise HTTPException(status_code=422, detail="resume_text is required")
    if not request.job_description:
        raise HTTPException(
            status_code=422,
            detail=(
                "job_description is required. A cover letter needs a role to "
                "write against -- without one the result would be a generic "
                "template, not a tailored artifact, so this endpoint refuses to "
                "generate one rather than producing something weak."
            ),
        )
    try:
        return generate_cover_letter(
            request.resume_text,
            request.job_description,
            request.tone
        )
    except CoverLetterError as e:
        # 502: the request to this endpoint was well-formed, generation
        # failed upstream (missing/invalid API key, Gemini request
        # failure, or a response that didn't parse) -- see
        # services/llm/client.py's LLMError, which CoverLetterError wraps.
        raise HTTPException(status_code=502, detail=str(e))


# ── /v2/analyze -- optional-JD analysis with the three-status model ───────────
#
# Distinct from /analyze (untouched, above): that route always requires a
# JD and returns the legacy flat-checks shape. /v2/analyze accepts an
# uploaded PDF directly (not pre-extracted text) so it can use all three
# parser channels -- text_layer, annotations, merged (Phase D) -- and the
# contact/link verification module (Phase E), neither of which /analyze's
# resume_text-in-JSON-out shape has access to. The JD is optional here:
# a scorer whose requires_jd is True (currently only Relevance) is simply
# never invoked (see services/analysis/pipeline.py), and every dimension
# result carries its own status (scored/uncomputable/not_applicable) so a
# caller can tell "ran and produced this score" apart from "didn't run."

@router.post("/v2/analyze")
async def analyze_resume_v2(
    file: UploadFile = File(...),
    job_description: str | None = Form(None),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    file_bytes = await file.read()
    try:
        extraction = extract_document(io.BytesIO(file_bytes))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse this PDF: {e}")

    if not extraction.is_readable:
        raise HTTPException(
            status_code=400,
            detail=(
                "This PDF has no extractable text -- it looks like a scanned "
                "image rather than a text-based document. Export or re-save "
                "it as a text PDF (not a scan) and try again."
            ),
        )

    # .merged, not .text -- carries invisible-annotation links (an icon-only
    # mailto:, say) that the text layer alone would never see. See
    # services/parsing/pdf_extract.py's module docstring.
    resume_text = normalize_document_text(extraction.merged)
    jd_text = normalize_document_text(job_description) if job_description else None

    analysis = run_analysis(resume_text, jd_text, _matcher)

    annotation_uris = [a.uri for a in extraction.annotations]
    contact_report = await build_report(resume_text, annotation_uris)

    return {
        **analysis.to_dict(),
        "parse": {
            "status": extraction.parse_status,
            "columns": extraction.column_counts,
            "unclickable_urls": extraction.unclickable_urls,
            "invisible_annotation_count": len(extraction.invisible_annotations),
        },
        "contact_links": {
            "summary": contact_report.summary,
            "issue_count": contact_report.issue_count,
            "phones": [
                {"raw": p.raw, "is_valid": p.is_valid, "e164": p.e164, "issue": p.issue}
                for p in contact_report.phones
            ],
            "emails": [
                {"raw": e.raw, "is_valid_syntax": e.is_valid_syntax,
                 "is_deliverable": e.is_deliverable, "issue": e.issue}
                for e in contact_report.emails
            ],
            "links": [
                {"url": l.url, "status": l.status.value, "http_status": l.http_status,
                 "platform_issue": l.platform_issue}
                for l in contact_report.links
            ],
            "missing": contact_report.completeness.missing if contact_report.completeness else [],
        },
    }