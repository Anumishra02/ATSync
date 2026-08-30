"""Cover letter generation (Phase G).

Deliberately its own small module, not folded into services/analysis/ or
services/scoring.py: cover letter generation is generative, not
evaluative. There is no rubric, no human labels, no correlation to
measure -- "is this cover letter good" isn't a question this codebase's
measurement discipline has an answer to, and it never will in the same
sense the scorers do. See README's Measurement section for why that's
stated outright rather than left ambiguous.

It also does NOT share services/analysis/models.py's three-status
(scored/uncomputable/not_applicable) JD-optional model. That model exists
because a *score* can meaningfully drop from /100 to /85 when a JD isn't
supplied -- fewer points were available, not zero. A cover letter has no
such partial mode: without a JD there's no role and no company to write
against, so the result would be a generic template, not a tailored
artifact. Rather than answer that request with something weak, the route
refuses it outright (422) -- the JD stays hard-required here specifically
because it's optional everywhere else in this codebase.
"""

from __future__ import annotations

from services.llm.client import LLMError, generate_json
from services.llm.prompts import load_prompt

_COVER_LETTER_SCHEMA = {
    "type": "object",
    "properties": {
        "cover_letter": {"type": "string"},
        "subject_line": {"type": "string"},
        "key_points": {"type": "array", "items": {"type": "string"}},
        "word_count": {"type": "integer"},
    },
    "required": ["cover_letter", "subject_line", "key_points", "word_count"],
}

# Same truncation the original implementation used -- keeps the prompt
# (and cost) bounded; not re-measured/re-tuned here, out of scope for this
# pass.
_RESUME_CHARS = 2000
_JD_CHARS = 1000

# A full 250-300 word, 4-paragraph letter plus the structured wrapper
# (subject line, key points, word count) is a much bigger generation job
# than grammar checking's few-sentence JSON reply -- generate_json's own
# 10s default (tuned for that faster call) was silently being used here
# too, since nothing overrode it. That's the likely cause of production
# timeouts on this route specifically, not a Gemini/model problem: the
# model here is already gemini-2.5-flash (see services/llm/client.py's
# DEFAULT_MODEL), not a slower Pro-tier model.
_COVER_LETTER_TIMEOUT_SECONDS = 60


class CoverLetterError(Exception):
    """Raised when a cover letter couldn't be generated. The route (not
    this module) decides what HTTP status that becomes.
    """


def generate_cover_letter(resume_text: str, job_description: str, tone: str = "professional") -> dict:
    prompt = load_prompt(
        "cover_letter",
        resume_text=resume_text[:_RESUME_CHARS],
        job_description=job_description[:_JD_CHARS],
        tone=tone,
    )
    try:
        data = generate_json(prompt, _COVER_LETTER_SCHEMA, timeout=_COVER_LETTER_TIMEOUT_SECONDS)
    except LLMError as e:
        raise CoverLetterError(str(e)) from e

    return {
        "cover_letter": data.get("cover_letter", ""),
        "subject_line": data.get("subject_line", ""),
        "key_points": data.get("key_points", []),
        "word_count": data.get("word_count", 0),
    }
