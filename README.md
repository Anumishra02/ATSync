# AI Resume Analyzer 🤖

A full-stack AI-powered platform that analyzes resumes against job descriptions.

## Features
- 📄 PDF Resume Upload and Parsing
- 📊 ATS Score with skill gap detection  
- 🎯 AI Interview Questions via Gemini API
- ✅ Matched and Missing Skills breakdown

## Tech Stack
- **Backend:** FastAPI, Python, PyPDF2, Google Gemini API
- **Frontend:** React, Tailwind CSS, Axios
- **AI/ML:** Keyword extraction, NLP-based ATS scoring

## Run Locally

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm start
```

## API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/resume/upload` | Upload PDF resume |
| POST | `/api/resume/score` | Get ATS score |
| POST | `/api/resume/interview-questions` | AI interview questions |
