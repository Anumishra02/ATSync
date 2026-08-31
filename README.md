<div align="center">

<img src="https://img.shields.io/badge/ATSync-AI%20Resume%20Analyzer-6366f1?style=for-the-badge&logoColor=white" />

# ATSync — AI Resume Analyzer & Interview Copilot

**Upload your resume. Get your ATS score. Land more interviews.**

A full-stack platform that scores resumes against a human-calibrated rubric, optionally against a job description, detects skill gaps, verifies contact info and links, and — separately, with no evaluation attached — generates interview questions and cover letters.

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Gemini](https://img.shields.io/badge/Google%20Gemini-4285F4?style=flat&logo=google&logoColor=white)](https://ai.google.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

## What is ATSync?

ATSync analyzes resumes against a rubric built from a 39-resume, human-labeled corpus (`evaluation/`) — not a keyword-count heuristic tuned to look reasonable. Every résumé in that corpus is a template with placeholder contact details (e.g. `(xxx) xxx-xxxx`, Canva's own `hello@reallygreatsite.com`), verified individually before being committed — no real people's data. Two analysis paths exist side by side:

- **`/api/resume/analyze`** (v1, live route) — the original flat 7-check engine (ATS keyword match, quantification, repetition, contact, file format, sections, grammar). Always requires a job description.
- **`/api/resume/v2/analyze`** (Phase G) — six rubric dimensions (Structure, Writing, Achievements, Skills, Experience, Relevance) scored through the three-status model (`scored` / `uncomputable` / `not_applicable`), an **optional** job description, the three-channel PDF parser (text layer + link annotations + merged), and real contact/link verification (phone validity, email deliverability, link reachability, platform-shape checks). See [Measurement & Evaluation](#measurement--evaluation) below for what that rubric is calibrated against and what it isn't.

## Measurement & Evaluation

This is the part most resume tools don't show, so it's stated explicitly here.

**What's measured.** The six dimensions behind `/v2/analyze` (`backend/services/analysis/`) are calibrated against `evaluation/labels.csv` — human scores for 39 real resumes, on the same rubric the scorers implement. Every scorer result carries a status, not just a number: `scored` (a real value was computed), `uncomputable` (the input gave the scorer nothing to work with — e.g. no bulleted content), or `not_applicable` (the dimension doesn't apply in the current mode, the canonical case being Relevance with no JD). Coverage — how often a dimension actually manages to run — is reported alongside accuracy, never folded into a single score, because a wide-coverage/low-accuracy system and a narrow-coverage/high-accuracy one fail in different ways and look identical if you only report one number.

Measured against the 39-resume corpus, coverage next to accuracy rather than either alone:

| mode | coverage | MAE | mean signed gap |
|---|---|---|---|
| quality (no JD) | 27/39 (69%) | 12.85 | −2.59 |
| match (with JD) | 27/39 (69%) | 17.36 | −8.74 |

Coverage below 70% means roughly 1 in 3 resumes hits at least one `uncomputable` dimension — that's the honest current ceiling on "produces a complete score," not a hidden caveat. Both modes score conservative relative to the human labels (negative gap). `.github/workflows/tests.yml` runs a regression gate (`backend/tests/test_structure_regression_gate.py`, `test_v2_analyze_regression_gate.py`) on every push and PR against exactly these two figures per mode, so they can't regress silently: it fails the build on a coverage drop or a mean-signed-gap shift in the wrong direction. It deliberately does **not** gate on Spearman ρ — at this sample size (n≈10–39 depending on split), ρ's own bootstrap confidence interval has spanned as wide as −0.23 to +0.96 across measurement runs, and quality mode's own ρ=0.260 isn't even significant (p=0.11) — too unstable to be a contract. See `evaluation/backlog.md` for the full measurement history, including findings that didn't work out (a taxonomy swap that improved coverage but nearly halved correlation; a JD-corpus rebuild that exposed a bigger coverage problem than the one it was measuring) and a full accounting of what each fix along the way contributed to the numbers above.

**What isn't measured, and won't be.** Interview-question and cover-letter generation (`backend/services/interview.py`, `backend/services/cover_letter.py`) are generative, not evaluative — there's no rubric for "is this a good interview question" or "is this cover letter good," no human labels, and no correlation to report. They're kept in their own modules, deliberately not entangled with the scoring pipeline or the evaluation harness, and don't share the three-status/JD-optional model above: a cover letter's job description is **hard-required** (see below), where a score's JD is optional. Generative and unevaluated, stated plainly here rather than left for a reader to assume otherwise.

**A component that got cut, on the record.** `backend/services/skills/README.md` documents a third skill-matching tier (embedding-cosine semantic matching) that was built, measured against a bar set *before* the numbers existed (recall > 0.60 and negative-trip-rate < 0.10), and removed when it didn't clear that bar — recall never exceeded ~0.46. It's linked here deliberately: a component that was evaluated and cut because it didn't help is stronger evidence of the measurement discipline this README describes than a component that was kept because it sounded advanced.

## Features

| Feature | Description |
|---|---|
| **Rubric-based Analysis** (`/v2/analyze`) | Six calibrated dimensions, optional JD, three-status coverage model |
| **ATS Score** (`/analyze`, `/score`) | Keyword/skill match against a job description |
| **Skill Gap Analysis** | Matched vs. missing skills against an ESCO-backed taxonomy |
| **Contact & Link Verification** | Real checks, not regex guesses: phone validity (`phonenumbers`), email deliverability via MX lookup (`email-validator`), link reachability (`httpx`), platform-shape rules (LinkedIn profile vs. search URL, etc.) |
| **Three-Channel PDF Parsing** | Text layer, link annotations, and their merge — catches icon-only mailto links and typed-but-unlinked URLs a text-only parser misses |
| **Quantification Check** | Detects achievement bullets missing numbers or measurable impact language |
| **Spelling & Grammar** | Gemini-backed, structured-output mode (not prompt-and-hope) |
| **AI Cover Letter** *(generative, unevaluated — see above)* | Tailored letter in five tones; refuses to generate without a job description |
| **AI Interview Questions** *(generative, unevaluated — see above)* | Technical, project, and behavioral questions specific to the resume |
| **Magnifier UI** | Interactive resume preview with a movable magnifying glass |

## Tech Stack

### Backend — `FastAPI + Python`

| Technology | Purpose |
|---|---|
| **FastAPI** | REST API framework — handles all HTTP endpoints |
| **Uvicorn** | ASGI server — runs the FastAPI application |
| **pdfplumber / pypdf / pdfminer.six** | Three-channel PDF text and link-annotation extraction |
| **google-generativeai** | Gemini access for grammar checking, interview questions, and cover letters — one shared client (`services/llm/client.py`), structured-output mode, no hand-rolled JSON parsing |
| **phonenumbers / email-validator / dnspython / httpx / tldextract** | Contact & link verification (`services/verification/`) |
| **sentence-transformers / rank_bm25 / wordfreq** | Skill matching and relevance scoring |
| **python-dotenv** | Loads `GEMINI_API_KEY` from `.env` |
| **Pydantic** | Request/response validation |

### Frontend — `React`

| Technology | Purpose |
|---|---|
| **React** | UI framework |
| **Axios** | HTTP client to the FastAPI backend |
| **CSS-in-JS** | All styles inline / in `<style>` tags — no external CSS framework |
| **Google Fonts (Inter)** | Typography |
| **SVG animations** | Score circle, magnifier glass, floating resume cards |

## Project Structure

```
ATSync/
├── backend/
│   ├── main.py                     # FastAPI app entry point + CORS config
│   ├── requirements.txt
│   ├── .env                        # GEMINI_API_KEY (not committed)
│   │
│   ├── routes/
│   │   └── resume.py               # /upload, /score, /analyze, /v2/analyze,
│   │                                # /cover-letter, /interview-questions
│   │
│   ├── services/
│   │   ├── analysis/                # v2 rubric: six scorers + three-status model
│   │   ├── parsing/pdf_extract.py   # three-channel PDF parser
│   │   ├── verification/contact_links.py  # phone/email/link verification
│   │   ├── skills/                  # taxonomy + skill matching
│   │   ├── llm/                     # shared Gemini client, prompt templates
│   │   ├── analyzer.py              # v1's 7-check engine
│   │   ├── cover_letter.py          # generative, unevaluated — its own module
│   │   ├── interview.py             # generative, unevaluated
│   │   └── parser.py                # legacy PyPDF2 text extraction (v1 fallback)
│   │
│   ├── tests/                       # pytest — fast suite + `slow` (network) marker
│   └── evaluation/                  # human-labeled corpus, eval scripts, backlog.md
│
├── evaluation/                      # 39-resume labels, JDs, measurement backlog
├── .github/workflows/tests.yml      # CI: full suite + regression gates
│
└── frontend/
    ├── public/
    └── src/
        └── App.js                   # entire React frontend (single-file architecture)
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/resume/upload` | Upload PDF → extract and return text |
| `POST` | `/api/resume/score` | ATS score against a job description |
| `POST` | `/api/resume/analyze` | v1: run all 7 flat checks, JD required |
| `POST` | `/api/resume/v2/analyze` | v2: six-dimension rubric, JD **optional**, contact/link verification + three-channel parsing wired in |
| `POST` | `/api/resume/interview-questions` | Generate AI interview questions *(generative, unevaluated)* |
| `POST` | `/api/resume/cover-letter` | Generate AI cover letter, JD **required** — 422 without one *(generative, unevaluated)* |
| `GET` | `/` | Health check |

---

## Setup & Run Locally

### Prerequisites

- Python 3.10+
- Node.js 18+
- Google Gemini API key — [get one free here](https://aistudio.google.com/app/apikeys) (only needed for grammar checking, interview questions, and cover letters — `/score`, `/analyze`, and `/v2/analyze`'s rubric dimensions don't call an LLM at all)

### Backend

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo "GEMINI_API_KEY=your_key_here" > .env

# Start server
uvicorn main:app --reload
# Runs on http://127.0.0.1:8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Optional: point the built app at a different backend without editing
# code. Falls back to the current production URL if unset.
echo "REACT_APP_API_URL=http://127.0.0.1:8000/api/resume" > .env.local

# Start dev server
npm start
# Opens at http://localhost:3000
```

### Tests

```bash
cd backend
python -m pytest -q          # fast suite (default: excludes `slow`)
python -m pytest -q -m slow  # network-dependent tests (MX lookups, HTTP HEAD)
```

## ATS Score Calculation (v1 — `/analyze`)

| Check | Weight |
|---|---|
| ATS Keyword Match | 30% |
| Quantification of Impact | 15% |
| Resume Sections | 15% |
| Spelling & Grammar | 10% |
| Contact Information | 10% |
| File Format & Size | 10% |
| Repetition | 10% |

`/v2/analyze`'s rubric uses a different weighting (Structure 15, Writing 15, Achievements 20, Skills 15, Experience 20, Relevance 15 — 100 points total, renormalized over whichever dimensions actually ran) — see [Measurement & Evaluation](#measurement--evaluation).


> Cover letter generator with 5 tone options

## What I Learned Building This

- Designing and building a **multi-endpoint FastAPI backend** with proper request validation using Pydantic
- Building an actual **measurement harness**: a human-labeled corpus, a regression gate wired into CI, and the discipline of reporting coverage next to accuracy instead of one number that hides which failure mode you're looking at
- Integrating **Google Gemini** behind one shared client with structured-output mode, instead of prompting for JSON and regex-parsing the response
- Building a **real NLP scoring system** using keyword extraction, normalization, and skill aliasing against an ESCO-backed taxonomy
- Creating a **production-quality React frontend** without any UI framework — just CSS-in-JS
- Handling **PDF parsing edge cases** — column-aware reading order, link annotations a text layer alone can't see, and text normalization
- Deploying and managing **CORS, environment variables, and API security** in a full-stack app

## Resume Line

> Built ATSync, an AI-powered resume analysis platform using FastAPI, React, and Google Gemini, with a rubric-based scoring engine calibrated against a 39-resume human-labeled corpus and gated by a CI regression suite, alongside NLP-based skill matching, contact/link verification, and AI-generated interview questions and cover letters — deployed as a full-stack REST API application.

## Author

**Anu Mishra** — Full Stack Developer & AI/ML Engineer

[![GitHub](https://img.shields.io/badge/GitHub-Anumishra02-black?style=flat&logo=github)](https://github.com/Anumishra02)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-anumish-blue?style=flat&logo=linkedin)](https://linkedin.com/in/anumish)

<div align="center">
    <sub>Built with care to help developers land their dream jobs</sub>
</div>
