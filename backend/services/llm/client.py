"""Shared Gemini client (Phase G).

Before this module, key resolution, timeout handling, and JSON-response
parsing were each written twice: once in services/analyzer.py's
check_grammar (google.generativeai SDK, no timeout, no missing-key guard),
once in services/cover_letter.py's generate_cover_letter (raw `requests`
against the REST endpoint directly, no timeout, no missing-key guard,
markdown-fence-stripped-then-json.loads()'d by hand). Both failed the same
way for the same reason -- no GEMINI_API_KEY configured -- and both would
have needed the same fix. This module is that fix, written once, so a
third call site (there already is one lying around unmigrated --
services/interview.py has the identical pattern) doesn't have to
re-discover it a third time.

Two things this module deliberately does NOT do:
  - Pick a fallback value on failure. check_grammar's "couldn't analyze"
    dict and the cover letter route's 422/502 responses are different,
    feature-specific answers to "the LLM call didn't work" -- this module
    only decides whether the call produced usable structured output, and
    raises LLMError when it didn't. Callers own the fallback.
  - Ask the model nicely for JSON in the prompt text and then regex/
    markdown-strip the response. Gemini's structured-output mode
    (response_mime_type="application/json" + response_schema) constrains
    the output server-side instead, so generate_json's callers pass a
    JSON-schema-shaped dict and get back parsed JSON or an error -- never
    a string that might or might not be valid JSON wrapped in ``` fences.

Only `google.generativeai` is used here, not raw `requests` -- one HTTP
path through the codebase, matching the SDK already used elsewhere, rather
than pinning `requests` (which was never a declared dependency; it worked
in cover_letter.py only because something else pulled it in transitively).
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import google.generativeai as genai
from dotenv import load_dotenv
from google.api_core.exceptions import DeadlineExceeded, ResourceExhausted

load_dotenv()

_API_KEY = os.getenv("GEMINI_API_KEY")
if _API_KEY:
    genai.configure(api_key=_API_KEY)

DEFAULT_MODEL = "gemini-2.5-flash"

# Per-attempt default -- callers with a longer job (cover letter generation
# vs. a grammar check) pass their own `timeout`, not a second module
# constant. See generate_json's docstring for why the retry below doesn't
# just reuse this value verbatim on a slow caller's second attempt.
DEFAULT_TIMEOUT_SECONDS = 10

# Render's reverse proxy (this app's current host) drops a request around
# ~100s with no error body at all -- not a Gemini error, not an HTTP
# status, just a closed connection. A client-side timeout exists so a slow
# call fails with a message instead of hanging forever; setting one longer
# than the proxy's own ceiling (or retrying in a way that pushes the total
# past it) defeats that -- it trades a clear LLMError for exactly the
# silent failure a timeout is supposed to prevent. Kept a few seconds
# under Render's own limit, not flush with it, for network/serialization
# overhead outside the Gemini call itself.
_PROXY_SAFE_CEILING_SECONDS = 90
_RETRY_BACKOFF_SECONDS = 2

# Used only when a 429 doesn't carry Google's own suggested wait (see
# _quota_retry_delay) -- a short guess, not a measured value.
_DEFAULT_QUOTA_BACKOFF_SECONDS = 5.0

# One model instance per model name, built on first use -- constructing a
# GenerativeModel is cheap, but there's no reason to redo it on every call
# when the same name is used repeatedly (both current call sites use the
# same default model).
_model_cache: dict[str, "genai.GenerativeModel"] = {}


class LLMError(Exception):
    """Raised for anything that keeps a Gemini call from producing usable
    structured output: no key configured, a request failure (network,
    timeout, non-200), or a response that isn't valid JSON matching the
    requested schema. Deliberately one type for all of these -- callers
    that want to distinguish "not configured" from "the network call
    failed" don't get that from this module; none of the two current
    callers need to.
    """


def is_configured() -> bool:
    return bool(_API_KEY)


def _get_model(model_name: str) -> "genai.GenerativeModel":
    if model_name not in _model_cache:
        _model_cache[model_name] = genai.GenerativeModel(model_name)
    return _model_cache[model_name]


def _quota_retry_delay(exc: ResourceExhausted) -> float:
    """A 429 from Gemini's API usually carries a structured RetryInfo
    error detail naming exactly how long to wait (confirmed against a
    real free-tier 429: ~36-39s, well past a short fixed backoff) --
    prefer that over a guess when it's present. Duck-typed on `.retry_delay`
    rather than isinstance-checked against google.rpc.error_details_pb2
    .RetryInfo, since that's less likely to break across library versions
    for the same reason services/llm/client.py prefers plain dicts over
    SDK-specific schema types elsewhere. Falls back to a short default
    when the detail isn't there (a differently-shaped error, or a
    transport that doesn't surface it).
    """
    for detail in getattr(exc, "details", None) or []:
        retry_delay = getattr(detail, "retry_delay", None)
        if retry_delay is not None:
            return retry_delay.seconds + retry_delay.nanos / 1e9
    return _DEFAULT_QUOTA_BACKOFF_SECONDS


def generate_json(
    prompt: str,
    response_schema: dict[str, Any],
    *,
    model: str = DEFAULT_MODEL,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    retries: int = 1,
) -> dict:
    """Calls Gemini with structured-output mode and returns the parsed
    JSON object. response_schema is a plain JSON-Schema-shaped dict
    (lowercase "type"/"properties"/"items"/"required" -- the SDK
    uppercases `type` internally); see cover_letter.py and analyzer.py for
    examples.

    `timeout` is a per-attempt budget in seconds, not a single global
    constant -- grammar checking and cover-letter generation have very
    different runtimes and pass their own value (10s / 60s respectively;
    see analyzer.py's _GRAMMAR_TIMEOUT_SECONDS and cover_letter.py's
    _COVER_LETTER_TIMEOUT_SECONDS).

    Two failure modes are retried, up to `retries` times each, with
    different backoffs:
      - DeadlineExceeded (the call was genuinely slow): a short fixed
        backoff (_RETRY_BACKOFF_SECONDS).
      - ResourceExhausted (a 429 -- confirmed on this project's own key,
        empirically, not anticipated): Google's own suggested wait, read
        from the response's RetryInfo detail when present (observed
        ~36-39s on a real quota hit -- see _quota_retry_delay), since a
        fixed short backoff can't plausibly clear a rate limit that takes
        that long to reset. Whether this genuinely helps in production
        (vs. a burst that's still rate-limited on retry) is exactly the
        kind of thing the retry-outcome logging below exists to answer
        with real traffic, not a guess.

    Either way, the retry's own timeout is capped so the running total
    (attempts + backoffs so far) never exceeds _PROXY_SAFE_CEILING_SECONDS,
    tracked from real elapsed time per attempt, not the requested timeout
    (a 429 typically fails almost instantly, well under its budget).
    Without that cap, a caller with a generous per-attempt timeout (cover
    letter's 60s) plus a naive same-length retry -- or a ~39s quota wait
    stacked on top of one -- could total well past Render's own ~100s
    proxy ceiling: trading one timeout (a clear LLMError) for another (a
    silently dropped connection with no error body at all). A short-
    timeout caller (grammar's 10s) has room to spare and is unaffected by
    the cap in practice.

    Any other API error isn't a "try again" failure, and retrying it
    isn't expected to help.

    Raises LLMError on any failure -- missing key, request failure
    (including a timeout or quota exhaustion that exhausts its retries),
    or a response that doesn't parse as JSON. Never returns a partial or
    best-effort result silently.
    """
    if not is_configured():
        raise LLMError("GEMINI_API_KEY is not configured")

    genai_model = _get_model(model)
    generation_config = genai.GenerationConfig(
        response_mime_type="application/json",
        response_schema=response_schema,
    )

    attempt_timeout = timeout
    total_elapsed = 0.0
    attempts_left = 1 + max(0, retries)
    attempt_number = 0

    # print, not a logging framework -- matches this codebase's existing
    # convention (see routes/resume.py's [upload] lines) and, on Render,
    # lands in the same place a logging call would. Deliberately logs
    # retry OUTCOME (attempted / succeeded-after-retry / exhausted), not
    # just that a failure happened -- whether either retry is worth
    # keeping is an empirical question production traffic can answer that
    # a single local measurement can't. If these never show "succeeded on
    # retry" for a given failure kind, retries=0 for the caller in
    # question is the change to make.
    while True:
        attempts_left -= 1
        attempt_number += 1
        attempt_start = time.monotonic()
        try:
            response = genai_model.generate_content(
                prompt,
                generation_config=generation_config,
                request_options={"timeout": attempt_timeout},
            )
            if attempt_number > 1:
                print(f"[llm.client] succeeded on retry (attempt {attempt_number}, timeout={attempt_timeout:.0f}s)")
            break
        except (DeadlineExceeded, ResourceExhausted) as e:
            total_elapsed += time.monotonic() - attempt_start
            is_quota = isinstance(e, ResourceExhausted)
            backoff = _quota_retry_delay(e) if is_quota else _RETRY_BACKOFF_SECONDS
            reason = "quota/rate limit" if is_quota else "DeadlineExceeded"
            next_timeout = min(timeout, _PROXY_SAFE_CEILING_SECONDS - total_elapsed - backoff)
            if attempts_left <= 0 or next_timeout <= 0:
                print(f"[llm.client] retries exhausted after {attempt_number} attempt(s) ({reason})")
                if is_quota:
                    raise LLMError(
                        "Gemini's request quota is exhausted for now. Please try again later."
                    ) from e
                raise LLMError("Gemini didn't respond in time. Please try again.") from e
            print(f"[llm.client] {reason} on attempt {attempt_number} -- retrying in {backoff:.0f}s with timeout={next_timeout:.0f}s")
            time.sleep(backoff)
            total_elapsed += backoff
            attempt_timeout = next_timeout
        except Exception as e:
            raise LLMError(f"Gemini request failed: {e}") from e

    try:
        return json.loads(response.text)
    except (ValueError, AttributeError) as e:
        raise LLMError(f"Gemini returned no parseable JSON: {e}") from e
