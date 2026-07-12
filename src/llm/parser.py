"""Response parsing helpers."""
from __future__ import annotations

import json
import re
from typing import Any

_CODE_FENCE_RE = re.compile(r"^```(?:json|text|python)?\s*|\s*```$", re.IGNORECASE)

# Categories whose prompts instruct the model to end with an "Answer: <x>" line.
_ANSWER_MARKER_CATEGORIES = frozenset(
    {"mathematical_reasoning", "logical_reasoning"}
)
# Matches the last "Answer:"/"Final answer:" line and captures everything after it.
_ANSWER_MARKER_RE = re.compile(
    r"(?:final\s+answer|answer)\s*[:=]\s*(.+?)\s*$",
    re.IGNORECASE | re.DOTALL,
)


def _strip_code_fences(text: str) -> str:
    return _CODE_FENCE_RE.sub("", text).strip()


def _extract_final_answer(text: str) -> str:
    """Return the text after the last 'Answer:' marker, else the full text.

    Keeps the model's reasoning out of the graded answer for math/logic tasks
    without discarding anything when no marker is present.
    """
    matches = list(_ANSWER_MARKER_RE.finditer(text))
    if not matches:
        return text
    answer = matches[-1].group(1).strip()
    return answer or text


def parse_response(response: Any, category: str) -> str:
    """Convert a Fireworks response into the final task answer string."""
    content = getattr(response, "content", response)
    if not isinstance(content, str):
        raise TypeError("Response content must be a string")

    cleaned = _strip_code_fences(content).strip()
    if category == "named_entity_recognition":
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            return cleaned
        return json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))

    if category in _ANSWER_MARKER_CATEGORIES:
        return _extract_final_answer(cleaned)

    return cleaned

