"""Tests for services/llm/client.py (Phase G) -- key resolution, timeout
plumbing, and structured-output error handling. No real network calls: the
SDK's GenerativeModel is monkeypatched out, matching this project's
CI-stays-network-free rule (see test_contact_links.py's docstring for the
same convention applied to a different module).
"""

from __future__ import annotations

import pytest
from google.api_core.exceptions import DeadlineExceeded, ResourceExhausted

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


class _SequenceModel:
    """Like _FakeModel, but a distinct outcome (an exception instance, or
    a response text) per call, in order -- for exercising retry behavior
    where the first attempt(s) fail and a later one succeeds (or all of
    them fail). The last entry repeats if more calls happen than entries
    given.
    """

    def __init__(self, outcomes: list):
        self._outcomes = outcomes
        self.calls: list[dict] = []

    def generate_content(self, prompt, **kwargs):
        self.calls.append({"prompt": prompt, **kwargs})
        outcome = self._outcomes[min(len(self.calls) - 1, len(self._outcomes) - 1)]
        if isinstance(outcome, Exception):
            raise outcome
        return _FakeResponse(outcome)


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


class TestGenerateJsonRetry:
    """Phase G loose end: cover letter generation was silently using
    generate_json's 10s default (tuned for grammar checking's much
    smaller job), the likely cause of production timeouts on that route.
    Fixed by making timeout a real per-call parameter (already possible,
    just never used) plus a bounded retry on DeadlineExceeded specifically.
    """

    def test_succeeds_on_retry_after_one_deadline_exceeded(self, monkeypatch):
        monkeypatch.setattr(llm_client, "_API_KEY", "fake-key")
        monkeypatch.setattr(llm_client.time, "sleep", lambda s: None)
        fake = _SequenceModel([DeadlineExceeded("slow"), '{"x": "hello"}'])
        monkeypatch.setattr(llm_client, "_get_model", lambda name: fake)

        result = generate_json("prompt", _SCHEMA, timeout=10)
        assert result == {"x": "hello"}
        assert len(fake.calls) == 2

    def test_exhausting_retries_raises_a_clear_message_not_the_raw_error(self, monkeypatch):
        # "surface a clear message rather than the raw Gemini error" --
        # the old generic path would have put the raw DeadlineExceeded
        # repr in the message; this one is meant to read plainly whatever
        # the client displays it as.
        monkeypatch.setattr(llm_client, "_API_KEY", "fake-key")
        monkeypatch.setattr(llm_client.time, "sleep", lambda s: None)
        fake = _SequenceModel([DeadlineExceeded("slow"), DeadlineExceeded("still slow")])
        monkeypatch.setattr(llm_client, "_get_model", lambda name: fake)

        with pytest.raises(LLMError, match="didn't respond in time") as exc_info:
            generate_json("prompt", _SCHEMA, timeout=10, retries=1)
        assert len(fake.calls) == 2
        assert "DeadlineExceeded" not in str(exc_info.value)

    def test_retries_zero_means_a_single_attempt(self, monkeypatch):
        monkeypatch.setattr(llm_client, "_API_KEY", "fake-key")
        monkeypatch.setattr(llm_client.time, "sleep", lambda s: None)
        fake = _SequenceModel([DeadlineExceeded("slow"), '{"x": "hello"}'])
        monkeypatch.setattr(llm_client, "_get_model", lambda name: fake)

        with pytest.raises(LLMError, match="didn't respond in time"):
            generate_json("prompt", _SCHEMA, timeout=10, retries=0)
        assert len(fake.calls) == 1

    def test_non_deadline_error_is_not_retried(self, monkeypatch):
        # A bad key or a network failure isn't "the response was just
        # slow" -- retrying it isn't expected to help, so it still fails
        # on the first attempt, same as before this change.
        monkeypatch.setattr(llm_client, "_API_KEY", "fake-key")
        monkeypatch.setattr(llm_client.time, "sleep", lambda s: None)
        fake = _SequenceModel([RuntimeError("connection reset"), '{"x": "hello"}'])
        monkeypatch.setattr(llm_client, "_get_model", lambda name: fake)

        with pytest.raises(LLMError, match="Gemini request failed"):
            generate_json("prompt", _SCHEMA, timeout=10)
        assert len(fake.calls) == 1

    def test_retry_timeout_is_capped_to_stay_under_the_proxy_ceiling(self, monkeypatch):
        # A caller with a generous per-attempt timeout (cover letter's
        # 60s) retrying at full length could total well past Render's own
        # ~100s proxy ceiling -- trading a clear LLMError for a silently
        # dropped connection instead. The retry's own timeout must shrink
        # to fit under _PROXY_SAFE_CEILING_SECONDS.
        monkeypatch.setattr(llm_client, "_API_KEY", "fake-key")
        monkeypatch.setattr(llm_client, "_PROXY_SAFE_CEILING_SECONDS", 90)
        monkeypatch.setattr(llm_client.time, "sleep", lambda s: None)
        fake = _SequenceModel([DeadlineExceeded("slow"), '{"x": "hello"}'])
        monkeypatch.setattr(llm_client, "_get_model", lambda name: fake)

        generate_json("prompt", _SCHEMA, timeout=60, retries=1)
        first_timeout = fake.calls[0]["request_options"]["timeout"]
        second_timeout = fake.calls[1]["request_options"]["timeout"]
        assert first_timeout == 60
        assert second_timeout < first_timeout
        assert second_timeout == pytest.approx(90 - 60 - 2)

    def test_quota_exhaustion_is_not_retried_and_gets_a_clear_message(self, monkeypatch):
        # Found empirically: running the eval corpus against a real
        # free-tier key hit a 429 (ResourceExhausted) well before any
        # genuine DeadlineExceeded did. Retrying it is pointless -- the
        # quota is exhausted for a window this client's 2s backoff can't
        # cover -- so it should fail on the first attempt with a message
        # that doesn't dump Gemini's raw multi-line quota-violation text.
        monkeypatch.setattr(llm_client, "_API_KEY", "fake-key")
        monkeypatch.setattr(llm_client.time, "sleep", lambda s: None)
        fake = _SequenceModel([ResourceExhausted("429 quota exceeded, retry_delay { seconds: 39 }")])
        monkeypatch.setattr(llm_client, "_get_model", lambda name: fake)

        with pytest.raises(LLMError, match="quota is exhausted") as exc_info:
            generate_json("prompt", _SCHEMA, timeout=10, retries=1)
        assert len(fake.calls) == 1
        assert "retry_delay" not in str(exc_info.value)

    def test_a_short_timeout_caller_gets_a_full_strength_retry(self, monkeypatch):
        # Grammar's 10s timeout has plenty of room under the ceiling --
        # the cap should not shrink its retry at all.
        monkeypatch.setattr(llm_client, "_API_KEY", "fake-key")
        monkeypatch.setattr(llm_client.time, "sleep", lambda s: None)
        fake = _SequenceModel([DeadlineExceeded("slow"), '{"x": "hello"}'])
        monkeypatch.setattr(llm_client, "_get_model", lambda name: fake)

        generate_json("prompt", _SCHEMA, timeout=10, retries=1)
        assert fake.calls[1]["request_options"]["timeout"] == 10


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
