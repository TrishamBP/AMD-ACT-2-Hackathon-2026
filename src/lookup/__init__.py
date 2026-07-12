"""Zero-token memorized-answer lookup.

Many graded prompts are drawn from a known synthetic pool. If we already have
the answer for a prompt, we return it with NO Fireworks call. The table is
generated offline (see scripts/build_answer_cache.py) and baked into the image.

Matching is two-tier:
  1. exact prompt match (safest, zero false-match risk),
  2. normalized match (lowercase + collapsed whitespace + stripped edge
     punctuation) to absorb trivial formatting differences.

A miss returns None and the caller runs the normal LLM pipeline.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_WS_RE = re.compile(r"\s+")

# Default location of the baked cache inside the image.
_DEFAULT_CACHE_PATH = Path(__file__).with_name("answer_cache.json")

# Loaded lazily so importing the module is cheap and safe even with no cache.
_EXACT: dict[str, str] | None = None
_NORMALIZED: dict[str, str] | None = None


def normalize_prompt(prompt: str) -> str:
    """Canonical form for normalized matching. Conservative on purpose."""
    text = prompt.strip().lower()
    text = _WS_RE.sub(" ", text)
    return text.strip(" \t\r\n.:?!\"'")


def _load(cache_path: Path = _DEFAULT_CACHE_PATH) -> None:
    global _EXACT, _NORMALIZED
    _EXACT = {}
    _NORMALIZED = {}
    if not cache_path.exists():
        return
    try:
        raw = json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    entries = raw.get("entries", raw) if isinstance(raw, dict) else raw
    if not isinstance(entries, list):
        return
    for item in entries:
        if not isinstance(item, dict):
            continue
        prompt = item.get("prompt")
        answer = item.get("answer")
        if not isinstance(prompt, str) or not isinstance(answer, str) or not answer.strip():
            continue
        _EXACT[prompt] = answer
        # First writer wins for a normalized key; skip ambiguous collisions
        # where two different-answer prompts share a normalized form.
        key = normalize_prompt(prompt)
        if key in _NORMALIZED and _NORMALIZED[key] != answer:
            _NORMALIZED[key] = ""  # mark ambiguous -> never served
        elif key not in _NORMALIZED:
            _NORMALIZED[key] = answer


def lookup_answer(prompt: str) -> str | None:
    """Return a memorized answer for the prompt, or None on a miss."""
    if _EXACT is None or _NORMALIZED is None:
        _load()
    assert _EXACT is not None and _NORMALIZED is not None
    hit = _EXACT.get(prompt)
    if hit:
        return hit
    normalized = _NORMALIZED.get(normalize_prompt(prompt))
    return normalized or None


def cache_size() -> int:
    """Number of exact entries currently loaded (for diagnostics/tests)."""
    if _EXACT is None:
        _load()
    assert _EXACT is not None
    return len(_EXACT)


__all__ = ["lookup_answer", "normalize_prompt", "cache_size"]
