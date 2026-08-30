"""Loads a named prompt template from services/llm/prompts/*.txt and fills
it with `.format(**kwargs)`. The thing being avoided is prompts built as
inline f-strings scattered across call sites (the state check_grammar and
cover_letter.py were both in before Phase G) -- one file per prompt, kept
next to the client that sends them, versionable and diffable on their own.

Templates hold plain instructions only, no literal JSON example to escape
-- output shape is enforced by generate_json's response_schema, not by
asking nicely in the prompt text, so there's no `{{`/`}}` bracket-escaping
to get wrong here.
"""

from __future__ import annotations

from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def load_prompt(name: str, **kwargs: str) -> str:
    template = (_PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8")
    return template.format(**kwargs)
