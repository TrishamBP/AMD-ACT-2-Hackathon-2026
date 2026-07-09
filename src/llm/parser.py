"""Response parsing helpers."""
from __future__ import annotations

import json
import re
from typing import Any

_CODE_FENCE_RE = re.compile(r"^```(?:json|text|python)?\s*|\s*```$", re.IGNORECASE)


def _strip_code_fences(text: str) -> str:
    return _CODE_FENCE_RE.sub("", text).strip()


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

    return cleaned

