"""Tests for /api/resume/upload -- the pdf_extract wiring and the
unreadable-document gate.

"Done when" bar from the plan this implements: the Canva file from the
real corpus, pushed through the live endpoint, returns contiguous
title/company/date -- asserted here, not eyeballed. And: every file in
the scanned batch returns unreadable; every synthetic fixture returns ok.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import app
from services.parsing import pdf_extract as pdf_extract_module

client = TestClient(app)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "pdfs"
REAL_CORPUS = Path(__file__).resolve().parents[2] / "test_corpus"
skip_without_real_corpus = pytest.mark.skipif(
    not REAL_CORPUS.exists(), reason="local-only real résumé corpus"
)


def _upload(path: Path):
    with open(path, "rb") as f:
        return client.post(
            "/api/resume/upload",
            files={"file": (path.name, f, "application/pdf")},
        )


class TestSyntheticFixturesUploadOk:
    @pytest.mark.parametrize(
        "filename",
        ["word_style.pdf", "canva_style.pdf", "two_column_template.pdf"],
    )
    def test_readable_fixture_uploads_successfully(self, filename):
        resp = _upload(FIXTURES / filename)
        assert resp.status_code == 200
        body = resp.json()
        assert body["characters"] > 0
        assert "Python" in body["full_text"]

    def test_non_pdf_extension_is_rejected(self, tmp_path):
        fake = tmp_path / "resume.txt"
        fake.write_text("not a pdf")
        with open(fake, "rb") as f:
            resp = client.post(
                "/api/resume/upload", files={"file": ("resume.txt", f, "text/plain")}
            )
        assert resp.status_code == 400


class TestFallbackToLegacyParser:
    def test_pdf_extract_failure_falls_back_to_pypdf2(self, monkeypatch):
        # pdf_extract raising shouldn't take the whole upload down -- the
        # fallback path should still return usable text.
        def _boom(_):
            raise RuntimeError("simulated pdfplumber failure")

        monkeypatch.setattr(pdf_extract_module, "extract_document", _boom)
        # routes.resume imported extract_document by name, so patch it there too.
        import routes.resume as resume_route

        monkeypatch.setattr(resume_route, "extract_document", _boom)

        resp = _upload(FIXTURES / "word_style.pdf")
        assert resp.status_code == 200
        assert "Python" in resp.json()["full_text"]


@skip_without_real_corpus
class TestRealCorpusUpload:
    def test_canva_export_returns_contiguous_title_company_date(self):
        path = REAL_CORPUS / "canva_pdf.pdf"
        if not path.exists():
            pytest.skip("canva_pdf.pdf not present locally")
        resp = _upload(path)
        assert resp.status_code == 200
        text = resp.json()["full_text"]

        # The bug this fixes: v1 (PyPDF2 content-stream order) scattered
        # "HCL Technologies", "AI/ML Intern", and the job's dates into three
        # disconnected clusters. Assert they now land within one contiguous
        # window of text, i.e. the same job entry.
        idx_company = text.find("HCL Technologies")
        idx_title = text.find("AI/ML Intern")
        idx_dates = text.find("June 2026")
        assert -1 not in (idx_company, idx_title, idx_dates), text[:500]
        window = sorted([idx_company, idx_title, idx_dates])
        assert window[-1] - window[0] < 200, (
            "company/title/dates should be close together, not scattered "
            f"({window[-1] - window[0]} chars apart)"
        )

    def test_scanned_files_are_rejected_as_unreadable(self):
        scanned = list(REAL_CORPUS.glob("resume *.pdf"))
        if not scanned:
            pytest.skip("scanned-batch files not present locally")
        for path in scanned:
            resp = _upload(path)
            assert resp.status_code == 400, path.name
            assert "scanned" in resp.json()["detail"].lower()
