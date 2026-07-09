"""Feature engineering for offline learning."""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any


@dataclass(slots=True)
class FeatureVector:
    """Feature vector for router training."""

    values: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class FeatureEngineer:
    """Extract deterministic routing features."""

    extra_extractors: list[Any] = field(default_factory=list)

    def transform(self, prompt: str) -> FeatureVector:
        text = prompt.lower()
        values: dict[str, float] = {
            "prompt_length": float(len(prompt)),
            "word_count": float(len(re.findall(r"\b\w+\b", prompt))),
            "has_code_fence": 1.0 if "```" in prompt else 0.0,
            "has_json": 1.0 if "{" in prompt and "}" in prompt else 0.0,
            "has_numbers": 1.0 if re.search(r"\d", prompt) else 0.0,
            "has_math_symbols": 1.0 if re.search(r"[\+\-\*/=^]", prompt) else 0.0,
            "has_summary_keywords": 1.0 if any(word in text for word in ("summarize", "summary")) else 0.0,
            "has_reasoning_keywords": 1.0 if any(word in text for word in ("logic", "deduce", "infer")) else 0.0,
            "has_code_keywords": 1.0 if any(word in text for word in ("python", "function", "class", "code")) else 0.0,
        }
        for extractor in self.extra_extractors:
            values.update(extractor(prompt))
        return FeatureVector(values=values)
