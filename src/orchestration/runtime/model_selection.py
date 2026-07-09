"""Model selection utilities for runtime inference."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


@dataclass(slots=True)
class ModelMetadata:
    """Parsed model capabilities."""

    id: str
    family: str
    params_billion: float | None
    instruction: bool = False
    reasoning: bool = False
    vision: bool = False
    raw: dict[str, Any] | None = None


def parse_allowed_models(models: list[str]) -> list[ModelMetadata]:
    """Parse allowed model identifiers into ranked metadata."""
    parsed = [_parse_model_metadata(model) for model in models]
    return sorted(parsed, key=lambda item: (item.params_billion or float("inf"), item.id))


class ModelSelector:
    """Choose the smallest compatible model."""

    def choose(
        self,
        allowed_models: list[str],
        *,
        needs_reasoning: bool = False,
        needs_vision: bool = False,
    ) -> ModelMetadata | None:
        candidates = parse_allowed_models(allowed_models)
        for candidate in candidates:
            if needs_reasoning and not candidate.reasoning:
                continue
            if needs_vision and not candidate.vision:
                continue
            return candidate
        return candidates[0] if candidates else None


def _parse_model_metadata(model_id: str) -> ModelMetadata:
    text = model_id.lower()
    family = model_id.split("-", 1)[0]
    params_billion = _extract_parameters(text)
    instruction = any(token in text for token in ("instruct", "instruction", "chat"))
    reasoning = any(token in text for token in ("reason", "thinking", "cot"))
    vision = any(token in text for token in ("vision", "vl", "multimodal"))
    return ModelMetadata(
        id=model_id,
        family=family,
        params_billion=params_billion,
        instruction=instruction,
        reasoning=reasoning,
        vision=vision,
        raw={"family": family, "text": text},
    )


def _extract_parameters(text: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*[bB]", text)
    if match:
        return float(match.group(1))
    moe = re.search(r"(\d+)x(\d+(?:\.\d+)?)\s*[bB]", text)
    if moe:
        return float(moe.group(1)) * float(moe.group(2))
    compact = re.search(r"(\d+(?:\.\d+)?)\s*m", text)
    if compact:
        return float(compact.group(1)) / 1000.0
    return None
