"""Guardrails for code debugging."""
from __future__ import annotations

from typing import Any

from src.orchestration.code_debugging.schemas import (
    CodeDebuggingInput,
    CodeDebuggingOutput,
)


class CodeDebuggingGuardrails:
    """Placeholder guardrails hooks for debugging."""

    def validate_input(self, payload: CodeDebuggingInput) -> CodeDebuggingInput:
        """Validate debugging input."""
        return payload

    def validate_output(
        self,
        payload: CodeDebuggingOutput | dict[str, Any],
    ) -> CodeDebuggingOutput:
        """Validate debugging output."""
        if isinstance(payload, CodeDebuggingOutput):
            return payload
        return CodeDebuggingOutput.model_validate(payload)

    def validate_length(self, code: str, *, limit: int = 8000) -> bool:
        """Validate output length."""
        return len(code) <= limit

    def check_hallucination(self, output: CodeDebuggingOutput) -> bool:
        """Placeholder hallucination check."""
        return True

    def validate_schema(self, payload: dict[str, Any]) -> CodeDebuggingOutput:
        """Validate output schema."""
        return CodeDebuggingOutput.model_validate(payload)
