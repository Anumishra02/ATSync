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
from typing import Any

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

_API_KEY = os.getenv("GEMINI_API_KEY")
if _API_KEY:
    genai.configure(api_key=_API_KEY)

DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_TIMEOUT_SECONDS = 10

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
) -> dict:
    """Calls Gemini with structured-output mode and returns the parsed
    JSON object. response_schema is a plain JSON-Schema-shaped dict
    (lowercase "type"/"properties"/"items"/"required" -- the SDK
    uppercases `type` internally); see cover_letter.py and analyzer.py for
    examples.

    Raises LLMError on any failure -- missing key, request failure, or a
    response that doesn't parse as JSON. Never returns a partial or
    best-effort result silently.
    """
    if not is_configured():
        raise LLMError("GEMINI_API_KEY is not configured")

    try:
        response = _get_model(model).generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
            ),
            request_options={"timeout": timeout},
        )
    except Exception as e:
        raise LLMError(f"Gemini request failed: {e}") from e

    try:
        return json.loads(response.text)
    except (ValueError, AttributeError) as e:
        raise LLMError(f"Gemini returned no parseable JSON: {e}") from e
