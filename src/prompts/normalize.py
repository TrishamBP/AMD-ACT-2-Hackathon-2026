"""Deterministic input normalization and budgeting for prompts.

Cuts input tokens before any Fireworks call without changing task semantics:
collapse whitespace/blank lines, strip conversational noise, and cap overly
long inputs per category. Pure functions, no I/O, no LLM.
"""
from __future__ import annotations

import re

_WHITESPACE_RE = re.compile(r"[ \t]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")
_TRAILING_WS_RE = re.compile(r"[ \t]+$", re.MULTILINE)

# Conversational filler often prepended/appended to prompts. Stripped only when
# it appears on its own line so we never remove meaningful content.
_NOISE_LINE_RE = re.compile(
    r"^\s*(?:thanks?(?: you)?|thank you|please|regards|best regards|cheers|"
    r"hi|hello|hey)[!,.]*\s*$",
    re.IGNORECASE,
)

# Approximate chars-per-token for budgeting (English ~4). Conservative.
_CHARS_PER_TOKEN = 4

# Max input characters per category. None = no cap (short inputs anyway).
# Summarization intentionally keeps a large budget so we don't drop content the
# summary must cover; other categories rarely need long inputs.
_INPUT_CHAR_BUDGET: dict[str, int | None] = {
    "text_summarization": 8000,
    "code_debugging": 4000,
    "code_generation": 3000,
    "factual_knowledge": 2000,
    "mathematical_reasoning": 2000,
    "logical_reasoning": 3000,
    "sentiment_classification": 3000,
    "named_entity_recognition": 3000,
}


def normalize_text(text: str) -> str:
    """Collapse whitespace, blank lines, and strip conversational noise."""
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = _WHITESPACE_RE.sub(" ", cleaned)
    cleaned = _TRAILING_WS_RE.sub("", cleaned)
    cleaned = _BLANK_LINES_RE.sub("\n\n", cleaned)

    # Drop standalone filler lines (greetings/sign-offs) without touching
    # lines that merely contain those words inside real content.
    kept = [line for line in cleaned.split("\n") if not _NOISE_LINE_RE.match(line)]
    cleaned = "\n".join(kept)

    return cleaned.strip()


def apply_input_budget(text: str, category: str) -> str:
    """Truncate input to the category's char budget, preserving both ends.

    Keeps the head and tail of over-long inputs (where instructions and the
    most salient content usually live) and marks the elision explicitly.
    """
    budget = _INPUT_CHAR_BUDGET.get(category)
    if budget is None or len(text) <= budget:
        return text

    marker = "\n...[content trimmed]...\n"
    keep = budget - len(marker)
    if keep <= 0:
        return text[:budget]
    head = keep * 2 // 3
    tail = keep - head
    return text[:head] + marker + text[-tail:]


def estimate_tokens(text: str) -> int:
    """Rough token estimate for regression tracking (chars / 4)."""
    return max(1, len(text) // _CHARS_PER_TOKEN)


def prepare_input(text: str, category: str) -> str:
    """Normalize then budget the raw task prompt for a category."""
    return apply_input_budget(normalize_text(text), category)
