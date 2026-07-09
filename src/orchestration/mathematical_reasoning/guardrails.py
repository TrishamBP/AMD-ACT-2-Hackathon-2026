"""Guardrails skeleton for mathematical reasoning."""
from __future__ import annotations

from typing import Any

from src.orchestration.mathematical_reasoning.schemas import MathProblem, MathResponse


class MathGuardrails:
    """Placeholder guardrails hooks for math tasks."""

    def validate_input(self, payload: MathProblem) -> MathProblem:
        """Validate math input."""
        return payload

    def validate_output(self, payload: MathResponse | dict[str, Any]) -> MathResponse:
        """Validate math output."""
        if isinstance(payload, MathResponse):
            return payload
        return MathResponse.model_validate(payload)

    def validate_length(self, answer: str, *, limit: int = 2048) -> bool:
        """Validate answer length."""
        return len(answer) <= limit

    def check_hallucination(self, output: MathResponse) -> bool:
        """Placeholder hallucination check."""
        return True

    def validate_schema(self, payload: dict[str, Any]) -> MathResponse:
        """Validate math schema."""
        return MathResponse.model_validate(payload)
