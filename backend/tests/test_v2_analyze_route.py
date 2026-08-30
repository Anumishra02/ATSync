"""Tests for /api/resume/v2/analyze (Phase G) -- the optional-JD route that
wires together run_analysis (three-status model), the three-channel parser,
and contact/link verification. /api/resume/analyze (v1) is untouched and
has its own tests; this file only covers the new route.

Network-touching checks (email deliverability MX lookup, link reachability
HTTP HEAD) are disabled here via monkeypatching build_report's defaults --
this file follows the same network-free-by-default convention as
test_contact_links.py rather than hitting the real network on every test
run.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import routes.resume as resume_route
from main import app

client = TestClient(app)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "pdfs"


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    # build_report(..., check_deliverability=, check_reachability=) default
    # to True in production (the whole point of wiring the module in) --
    # for these tests, wrap it so they run offline like the rest of the
    # fast suite.
    import services.verification.contact_links as contact_links_module

    real_build_report = contact_links_module.build_report

    async def _offline_build_report(text, annotation_uris=None, **kwargs):
        kwargs.setdefault("check_deliverability", False)
        kwargs.setdefault("check_reachability", False)
        return await real_build_report(text, annotation_uris, **kwargs)

    monkeypatch.setattr(resume_route, "build_report", _offline_build_report)


def _analyze(path: Path, job_description: str | None = None):
    data = {"job_description": job_description} if job_description else {}
    with open(path, "rb") as f:
        return client.post(
            "/api/resume/v2/analyze",
            files={"file": (path.name, f, "application/pdf")},
            data=data,
        )


class TestModeSelection:
    def test_no_jd_runs_in_quality_mode(self):
        resp = _analyze(FIXTURES / "canva_style.pdf")
        assert resp.status_code == 200
        body = resp.json()
        assert body["mode"] == "quality"
        relevance = next(d for d in body["dimensions"] if d["dimension"] == "relevance")
        assert relevance["status"] == "not_applicable"

    def test_jd_supplied_runs_in_match_mode(self):
        resp = _analyze(
            FIXTURES / "canva_style.pdf",
            job_description="Looking for a Python and FastAPI backend engineer.",
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["mode"] == "match"
        relevance = next(d for d in body["dimensions"] if d["dimension"] == "relevance")
        assert relevance["status"] == "scored"


class TestResponseShape:
    def test_carries_parse_and_contact_link_sections(self):
        resp = _analyze(FIXTURES / "canva_style.pdf")
        body = resp.json()
        assert "parse" in body
        assert "status" in body["parse"]
        assert "contact_links" in body
        assert "summary" in body["contact_links"]
        assert "issue_count" in body["contact_links"]

    def test_every_dimension_carries_a_status(self):
        resp = _analyze(FIXTURES / "canva_style.pdf")
        for d in resp.json()["dimensions"]:
            assert d["status"] in ("scored", "uncomputable", "not_applicable")


class TestRejections:
    def test_non_pdf_extension_is_rejected(self, tmp_path):
        fake = tmp_path / "resume.txt"
        fake.write_text("not a pdf")
        with open(fake, "rb") as f:
            resp = client.post(
                "/api/resume/v2/analyze", files={"file": ("resume.txt", f, "text/plain")}
            )
        assert resp.status_code == 400

    def test_v1_analyze_route_is_unaffected(self):
        # /analyze still takes pre-extracted text + a required JD -- Phase G
        # explicitly left this route untouched.
        resp = client.post(
            "/api/resume/analyze",
            json={
                "resume_text": "Experience\nBuilt things.\n",
                "job_description": "Looking for an engineer.",
                "filename": "resume.pdf",
                "file_size": 1000,
            },
        )
        assert resp.status_code == 200
        assert "categories" in resp.json()
