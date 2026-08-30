"""Tests for services/cover_letter.py and the /api/resume/cover-letter
route (Phase G fix). No real Gemini calls -- services.llm.client.generate_json
is monkeypatched, same convention as test_llm_client.py.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import services.cover_letter as cover_letter_module
from main import app
from services.cover_letter import CoverLetterError, generate_cover_letter
from services.llm.client import LLMError

client = TestClient(app)


class TestGenerateCoverLetter:
    def test_returns_the_parsed_fields_on_success(self, monkeypatch):
        monkeypatch.setattr(
            cover_letter_module,
            "generate_json",
            lambda prompt, schema: {
                "cover_letter": "Dear Hiring Manager...",
                "subject_line": "Application for Backend Engineer - Jane Doe",
                "key_points": ["Python", "FastAPI"],
                "word_count": 270,
            },
        )
        result = generate_cover_letter("resume text", "job description", "professional")
        assert result["cover_letter"] == "Dear Hiring Manager..."
        assert result["word_count"] == 270

    def test_llm_error_becomes_cover_letter_error(self, monkeypatch):
        # The bug this class exists to fix: an unconfigured/failing key
        # used to surface as a bare Exception with Gemini's raw response
        # text in it. Now it's a typed, catchable error the route maps to
        # a specific HTTP status.
        def _boom(prompt, schema):
            raise LLMError("GEMINI_API_KEY is not configured")

        monkeypatch.setattr(cover_letter_module, "generate_json", _boom)
        with pytest.raises(CoverLetterError):
            generate_cover_letter("resume text", "job description")


class TestCoverLetterRoute:
    def test_missing_job_description_is_422_not_a_weak_generation(self):
        # Design decision (Phase G): a cover letter without a JD is refused
        # outright, not generated as a generic template.
        resp = client.post(
            "/api/resume/cover-letter",
            json={"resume_text": "Experienced engineer.", "job_description": ""},
        )
        assert resp.status_code == 422
        assert "job_description" in resp.json()["detail"]

    def test_missing_resume_text_is_422(self):
        resp = client.post(
            "/api/resume/cover-letter",
            json={"resume_text": "", "job_description": "Backend role."},
        )
        assert resp.status_code == 422

    def test_generation_failure_is_502_not_500(self, monkeypatch):
        def _boom(prompt, schema):
            raise LLMError("GEMINI_API_KEY is not configured")

        monkeypatch.setattr(cover_letter_module, "generate_json", _boom)
        resp = client.post(
            "/api/resume/cover-letter",
            json={"resume_text": "Experienced engineer.", "job_description": "Backend role."},
        )
        assert resp.status_code == 502

    def test_successful_generation_returns_the_letter(self, monkeypatch):
        monkeypatch.setattr(
            cover_letter_module,
            "generate_json",
            lambda prompt, schema: {
                "cover_letter": "Dear Hiring Manager...",
                "subject_line": "Application for Backend Engineer - Jane Doe",
                "key_points": ["Python"],
                "word_count": 260,
            },
        )
        resp = client.post(
            "/api/resume/cover-letter",
            json={"resume_text": "Experienced engineer.", "job_description": "Backend role."},
        )
        assert resp.status_code == 200
        assert resp.json()["subject_line"] == "Application for Backend Engineer - Jane Doe"
