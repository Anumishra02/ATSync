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


class _FakeDuration:
    def __init__(self, seconds: int, nanos: int = 0):
        self.seconds = seconds
        self.nanos = nanos


class _FakeRetryInfo:
    """Duck-types google.rpc.error_details_pb2.RetryInfo well enough for
    _quota_retry_delay's getattr-based extraction -- deliberately not the
    real proto type, matching _quota_retry_delay's own choice not to
    isinstance-check against it.
    """

    def __init__(self, seconds: int, nanos: int = 0):
        self.retry_delay = _FakeDuration(seconds, nanos)


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
        # to fit under _PROXY_SAFE_CEILING_SECONDS. Budget tracking is real
        # elapsed time now (a fast-failing 429 shouldn't eat its whole
        # requested timeout out of the budget) -- a real DeadlineExceeded
        # genuinely does consume close to its full attempt_timeout (that's
        # what "exceeded the deadline" means), simulated here with a fake
        # clock rather than relying on a mock call that fails instantly.
        monkeypatch.setattr(llm_client, "_API_KEY", "fake-key")
        monkeypatch.setattr(llm_client, "_PROXY_SAFE_CEILING_SECONDS", 90)
        monkeypatch.setattr(llm_client.time, "sleep", lambda s: None)
        clock = iter([0.0, 60.0, 60.0, 60.0])
        monkeypatch.setattr(llm_client.time, "monotonic", lambda: next(clock))
        fake = _SequenceModel([DeadlineExceeded("slow"), '{"x": "hello"}'])
        monkeypatch.setattr(llm_client, "_get_model", lambda name: fake)

        generate_json("prompt", _SCHEMA, timeout=60, retries=1)
        first_timeout = fake.calls[0]["request_options"]["timeout"]
        second_timeout = fake.calls[1]["request_options"]["timeout"]
        assert first_timeout == 60
        assert second_timeout < first_timeout
        assert second_timeout == pytest.approx(90 - 60 - 2)

    def test_quota_exhaustion_is_retried_using_googles_own_retry_delay(self, monkeypatch):
        # Found empirically: running the eval corpus against a real
        # free-tier key hit a 429 (ResourceExhausted) well before any
        # genuine DeadlineExceeded did -- confirmed via AI Studio's usage
        # dashboard to be batch/eval-script traffic tripping a per-minute
        # cap, not sustained exhaustion, so a retry using Google's own
        # suggested wait (not this client's short DeadlineExceeded backoff)
        # is worth attempting rather than failing immediately.
        monkeypatch.setattr(llm_client, "_API_KEY", "fake-key")
        monkeypatch.setattr(llm_client.time, "sleep", lambda s: None)
        error = ResourceExhausted("429 quota exceeded", details=[_FakeRetryInfo(seconds=39)])
        fake = _SequenceModel([error, '{"x": "hello"}'])
        monkeypatch.setattr(llm_client, "_get_model", lambda name: fake)

        result = generate_json("prompt", _SCHEMA, timeout=10, retries=1)
        assert result == {"x": "hello"}
        assert len(fake.calls) == 2

    def test_quota_retry_uses_googles_delay_not_the_deadline_backoff(self, monkeypatch):
        monkeypatch.setattr(llm_client, "_API_KEY", "fake-key")
        sleeps = []
        monkeypatch.setattr(llm_client.time, "sleep", sleeps.append)
        error = ResourceExhausted("429 quota exceeded", details=[_FakeRetryInfo(seconds=39)])
        fake = _SequenceModel([error, '{"x": "hello"}'])
        monkeypatch.setattr(llm_client, "_get_model", lambda name: fake)

        generate_json("prompt", _SCHEMA, timeout=10, retries=1)
        assert sleeps == [39.0]

    def test_quota_error_without_retry_delay_detail_falls_back_to_a_default(self, monkeypatch):
        # A 429 whose response doesn't carry a RetryInfo detail (a
        # differently-shaped error, or a transport that doesn't surface
        # it) shouldn't crash the retry logic -- falls back to a short
        # default rather than failing to parse.
        monkeypatch.setattr(llm_client, "_API_KEY", "fake-key")
        sleeps = []
        monkeypatch.setattr(llm_client.time, "sleep", sleeps.append)
        error = ResourceExhausted("429 quota exceeded, no details attached")
        fake = _SequenceModel([error, '{"x": "hello"}'])
        monkeypatch.setattr(llm_client, "_get_model", lambda name: fake)

        result = generate_json("prompt", _SCHEMA, timeout=10, retries=1)
        assert result == {"x": "hello"}
        assert sleeps == [llm_client._DEFAULT_QUOTA_BACKOFF_SECONDS]

    def test_quota_exhaustion_exhausting_retries_gets_a_clear_message(self, monkeypatch):
        # Repeated 429s (quota genuinely still exhausted, not just an
        # unlucky burst) still end in a message that doesn't dump Gemini's
        # raw multi-line quota-violation text.
        monkeypatch.setattr(llm_client, "_API_KEY", "fake-key")
        monkeypatch.setattr(llm_client.time, "sleep", lambda s: None)
        error = ResourceExhausted("429 quota exceeded", details=[_FakeRetryInfo(seconds=1)])
        fake = _SequenceModel([error, error])
        monkeypatch.setattr(llm_client, "_get_model", lambda name: fake)

        with pytest.raises(LLMError, match="quota is exhausted") as exc_info:
            generate_json("prompt", _SCHEMA, timeout=10, retries=1)
        assert len(fake.calls) == 2
        assert "retry_delay" not in str(exc_info.value)

    def test_quota_retry_is_also_capped_to_the_proxy_ceiling(self, monkeypatch):
        # A ~39s quota wait stacked on top of a generous per-attempt
        # timeout (cover letter's 60s) could push the total past Render's
        # ~100s ceiling just as easily as a same-length DeadlineExceeded
        # retry would -- the cap applies to either failure kind.
        monkeypatch.setattr(llm_client, "_API_KEY", "fake-key")
        monkeypatch.setattr(llm_client, "_PROXY_SAFE_CEILING_SECONDS", 90)
        monkeypatch.setattr(llm_client.time, "sleep", lambda s: None)
        error = ResourceExhausted("429 quota exceeded", details=[_FakeRetryInfo(seconds=39)])
        fake = _SequenceModel([error, '{"x": "hello"}'])
        monkeypatch.setattr(llm_client, "_get_model", lambda name: fake)

        generate_json("prompt", _SCHEMA, timeout=60, retries=1)
        second_timeout = fake.calls[1]["request_options"]["timeout"]
        # 429s fail near-instantly (real elapsed time, not the requested
        # timeout, is what's charged against the budget) -- ~90 - ~0 - 39.
        assert second_timeout == pytest.approx(90 - 39, abs=1)

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
