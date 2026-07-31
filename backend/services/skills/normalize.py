"""Text normalization and tokenization for skill matching.

Everything downstream depends on one invariant: we compare *tokens*, never
raw substrings. This is what stops "java" matching inside "JavaScript" and
"oop" matching inside "loops".
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# Characters that are legitimately part of a technical term and must survive
# tokenization: c++, c#, node.js, ci/cd, object-oriented.
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+#.\-/]*")

# Unicode dashes and quotes that PDFs love to emit.
_DASHES = dict.fromkeys(map(ord, "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"), "-")


@dataclass(frozen=True, slots=True)
class Token:
    """A single token plus its position in the original (normalized) text."""

    text: str
    start: int
    end: int


def normalize(text: str) -> str:
    """Lowercase, fold unicode, unify dashes. Length-preserving where possible."""
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_DASHES)
    return text.lower()


def tokenize(text: str) -> list[Token]:
    """Split normalized text into tokens, keeping char offsets for highlighting."""
    tokens: list[Token] = []
    for m in _TOKEN_RE.finditer(text):
        raw = m.group(0)
        # Strip trailing sentence punctuation ("node.js." -> "node.js")
        stripped = raw.rstrip("./-")
        if not stripped:
            continue
        tokens.append(Token(text=stripped, start=m.start(), end=m.start() + len(stripped)))
    return tokens


def phrase_key(text: str) -> str:
    """Canonical lookup key for a phrase.

    Collapses hyphens to spaces so "object-oriented programming" and
    "object oriented programming" hash to the same bucket, while leaving
    "c++", "c#" and "ci/cd" intact.
    """
    tokens = [t.text for t in tokenize(normalize(text))]
    return " ".join(tokens).replace("-", " ")


def ngram_keys(tokens: list[Token], max_n: int = 4):
    """Yield (key, start_token_idx, end_token_idx) for every 1..max_n gram.

    Emitted longest-first so the matcher can greedily prefer "machine learning"
    over a bare "learning".
    """
    n_tokens = len(tokens)
    for n in range(min(max_n, n_tokens), 0, -1):
        for i in range(n_tokens - n + 1):
            window = tokens[i : i + n]
            key = " ".join(t.text for t in window).replace("-", " ")
            yield key, i, i + n
