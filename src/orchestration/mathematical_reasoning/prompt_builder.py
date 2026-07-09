"""Compact prompt builder for math tasks."""
from __future__ import annotations

from src.orchestration.mathematical_reasoning.schemas import MathProblem, ParsedProblem


def build_math_prompt(problem: MathProblem, parsed: ParsedProblem) -> str:
    """Build a compact single-shot math prompt."""
    return (
        "Solve the problem. Return only the final answer.\n"
        f"Type: {parsed.problem_type}\n"
        f"Numbers: {', '.join(str(number) for number in parsed.numbers) or 'none'}\n"
        f"Variables: {', '.join(parsed.variables) or 'none'}\n"
        f"Constraints: {', '.join(parsed.constraints) or 'none'}\n"
        f"Problem: {problem.statement.strip()}"
    )


def build_math_repair_prompt(
    problem: MathProblem,
    parsed: ParsedProblem,
    answer: str,
    validation_errors: list[str],
) -> str:
    """Build a tiny repair prompt."""
    errors = ", ".join(validation_errors) if validation_errors else "validation_failed"
    return (
        "Fix the math answer.\n"
        f"Type: {parsed.problem_type}\n"
        f"Errors: {errors}\n"
        "Return only the corrected answer.\n"
        f"Problem: {problem.statement.strip()}\n"
        f"Answer: {answer.strip()}"
    )
