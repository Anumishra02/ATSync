"""Tests for services/llm/client.py (Phase G) -- key resolution, timeout
plumbing, and structured-output error handling. No real network calls: the
SDK's GenerativeModel is monkeypatched out, matching this project's
CI-stays-network-free rule (see test_contact_links.py's docstring for the
same convention applied to a different module).
"""

from __future__ import annotations

import pytest

from services.llm import client as llm_client
from services.llm.client import LLMError, generate_json, is_configured
from services.llm.prompts import load_prompt

_SCHEMA = {"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]}


class _FakeResponse:
    def __init__(self, text: str):
        self.text = text


class _FakeModel:
    def __init__(self, text: str | None = None, raises: Exception | None = None):
        self._text = text
        self._raises = raises
        self.calls: list[dict] = []

    def generate_content(self, prompt, **kwargs):
        self.calls.append({"prompt": prompt, **kwargs})
        if self._raises is not None:
            raise self._raises
        return _FakeResponse(self._text)


class TestIsConfigured:
    def test_false_when_no_key(self, monkeypatch):
        monkeypatch.setattr(llm_client, "_API_KEY", None)
        assert is_configured() is False

    def test_true_when_key_present(self, monkeypatch):
        monkeypatch.setattr(llm_client, "_API_KEY", "fake-key")
        assert is_configured() is True


class TestGenerateJsonMissingKey:
    def test_raises_without_calling_the_model(self, monkeypatch):
        # The whole point of the early-return guard this replaces (see
        # client.py's module docstring): no key means every call would
        # fail anyway, so don't make (and wait on) one.
        monkeypatch.setattr(llm_client, "_API_KEY", None)
        with pytest.raises(LLMError, match="not configured"):
            generate_json("prompt", _SCHEMA)


class TestGenerateJsonSuccess:
    def test_parses_the_response_text_as_json(self, monkeypatch):
        monkeypatch.setattr(llm_client, "_API_KEY", "fake-key")
        fake = _FakeModel(text='{"x": "hello"}')
        monkeypatch.setattr(llm_client, "_get_model", lambda name: fake)

        result = generate_json("prompt", _SCHEMA)
        assert result == {"x": "hello"}

    def test_passes_response_schema_and_mime_type_through(self, monkeypatch):
        # This is the structured-output contract itself -- the model must
        # be told to constrain its output, not just asked nicely in the
        # prompt text (the pattern this module replaces).
        monkeypatch.setattr(llm_client, "_API_KEY", "fake-key")
        fake = _FakeModel(text='{"x": "hello"}')
        monkeypatch.setattr(llm_client, "_get_model", lambda name: fake)

        generate_json("prompt", _SCHEMA, timeout=5)
        call = fake.calls[0]
        assert call["generation_config"].response_mime_type == "application/json"
        assert call["generation_config"].response_schema == _SCHEMA
        assert call["request_options"] == {"timeout": 5}


class TestGenerateJsonFailureModes:
    def test_request_failure_becomes_llm_error(self, monkeypatch):
        monkeypatch.setattr(llm_client, "_API_KEY", "fake-key")
        fake = _FakeModel(raises=RuntimeError("connection reset"))
        monkeypatch.setattr(llm_client, "_get_model", lambda name: fake)

        with pytest.raises(LLMError, match="Gemini request failed"):
            generate_json("prompt", _SCHEMA)

    def test_unparseable_response_becomes_llm_error(self, monkeypatch):
        monkeypatch.setattr(llm_client, "_API_KEY", "fake-key")
        fake = _FakeModel(text="not json at all")
        monkeypatch.setattr(llm_client, "_get_model", lambda name: fake)

        with pytest.raises(LLMError, match="no parseable JSON"):
            generate_json("prompt", _SCHEMA)


class TestLoadPrompt:
    def test_fills_in_placeholders(self):
        # grammar_check.txt has a single {text} placeholder.
        rendered = load_prompt("grammar_check", text="Hello world")
        assert "Hello world" in rendered

    def test_cover_letter_prompt_fills_all_three_placeholders(self):
        rendered = load_prompt(
            "cover_letter", resume_text="RESUME BODY", job_description="JD BODY", tone="casual",
        )
        assert "RESUME BODY" in rendered
        assert "JD BODY" in rendered
        assert "casual" in rendered
