"""Compact prompt builder for logical reasoning."""
from __future__ import annotations

from src.orchestration.logical_reasoning.schemas import (
    LogicalReasoningInput,
    ParsedLogicalProblem,
)


def build_logical_reasoning_prompt(
    payload: LogicalReasoningInput,
    parsed: ParsedLogicalProblem,
) -> str:
    """Build a compact fallback prompt."""
    return (
        "Solve the logic problem.\n"
        f"Type: {parsed.reasoning_type}\n"
        f"Variables: {', '.join(parsed.variables) or 'none'}\n"
        f"Constraints: {', '.join(parsed.constraints) or 'none'}\n"
        "Return only the final answer.\n"
        f"Problem: {payload.request.strip()}"
    )


def build_logical_reasoning_repair_prompt(
    payload: LogicalReasoningInput,
    parsed: ParsedLogicalProblem,
    answer: str,
    validation_errors: list[str],
) -> str:
    """Build a tiny repair prompt."""
    errors = ", ".join(validation_errors) if validation_errors else "validation_failed"
    return (
        "Repair the logic answer.\n"
        f"Type: {parsed.reasoning_type}\n"
        f"Errors: {errors}\n"
        "Return only the corrected answer.\n"
        f"Problem: {payload.request.strip()}\n"
        f"Answer: {answer.strip()}"
    )
