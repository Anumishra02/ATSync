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
    _COVER_LETTER_TIMEOUT_SECONDS). On a DeadlineExceeded, retries up to
    `retries` times after a short backoff -- but each retry's own timeout
    is capped so the running total (attempts + backoffs so far) never
    exceeds _PROXY_SAFE_CEILING_SECONDS. Without that cap, a caller with a
    generous per-attempt timeout (cover letter's 60s) plus a naive same-
    length retry could total well past Render's own ~100s proxy ceiling --
    trading one timeout (a clear LLMError) for another (a silently dropped
    connection with no error body at all). A short-timeout caller
    (grammar's 10s) is unaffected by the cap in practice and still gets a
    full-strength retry.

    Only DeadlineExceeded is retried -- a bad key, a network failure, or
    any other API error isn't a "the response was just slow" failure, and
    retrying it isn't expected to help.

    Raises LLMError on any failure -- missing key, request failure
    (including a timeout that exhausts its retries), or a response that
    doesn't parse as JSON. Never returns a partial or best-effort result
    silently.
    """
    if not is_configured():
        raise LLMError("GEMINI_API_KEY is not configured")

    genai_model = _get_model(model)
    generation_config = genai.GenerationConfig(
        response_mime_type="application/json",
        response_schema=response_schema,
    )

    attempt_timeout = timeout
    elapsed_budget = 0.0
    attempts_left = 1 + max(0, retries)
    attempt_number = 0

    # print, not a logging framework -- matches this codebase's existing
    # convention (see routes/resume.py's [upload] lines) and, on Render,
    # lands in the same place a logging call would. Deliberately logs
    # retry OUTCOME (attempted / succeeded-after-retry / exhausted), not
    # just that a timeout happened -- whether a retry is worth keeping is
    # an empirical question (a DeadlineExceeded on a job that's genuinely
    # slow, not just unlucky, will likely fail again at a shorter budget
    # too), and that needs production evidence, not a guess in either
    # direction. If these never show "succeeded on retry", retries=0 for
    # the caller in question is the change to make.
    while True:
        attempts_left -= 1
        attempt_number += 1
        try:
            response = genai_model.generate_content(
                prompt,
                generation_config=generation_config,
                request_options={"timeout": attempt_timeout},
            )
            if attempt_number > 1:
                print(f"[llm.client] succeeded on retry (attempt {attempt_number}, timeout={attempt_timeout:.0f}s)")
            break
        except DeadlineExceeded as e:
            elapsed_budget += attempt_timeout + _RETRY_BACKOFF_SECONDS
            next_timeout = min(timeout, _PROXY_SAFE_CEILING_SECONDS - elapsed_budget)
            if attempts_left <= 0 or next_timeout <= 0:
                print(f"[llm.client] retries exhausted after {attempt_number} attempt(s), last timeout={attempt_timeout:.0f}s")
                raise LLMError(
                    "Gemini didn't respond in time. Please try again."
                ) from e
            print(f"[llm.client] DeadlineExceeded on attempt {attempt_number} (timeout={attempt_timeout:.0f}s) -- retrying with timeout={next_timeout:.0f}s")
            time.sleep(_RETRY_BACKOFF_SECONDS)
            attempt_timeout = next_timeout
        except ResourceExhausted as e:
            # Found empirically, not anticipated -- running this module's
            # own eval-corpus check against a real (free-tier) key hit
            # this within the first few calls: quota, not a timeout, was
            # the failure this project's own key hit first. Not retried --
            # Google's own retry_delay on this response is measured in
            # tens of seconds to a day depending on which quota tripped,
            # not this module's 2s backoff, so retrying immediately can't
            # help and only spends another attempt against the same
            # exhausted quota.
            print(f"[llm.client] quota/rate limit hit on attempt {attempt_number}: {e}")
            raise LLMError(
                "Gemini's request quota is exhausted for now. Please try again later."
            ) from e
        except Exception as e:
            raise LLMError(f"Gemini request failed: {e}") from e

    try:
        return json.loads(response.text)
    except (ValueError, AttributeError) as e:
        raise LLMError(f"Gemini returned no parseable JSON: {e}") from e
