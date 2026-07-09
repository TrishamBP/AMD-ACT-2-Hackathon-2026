"""Compact prompt builder for code debugging."""
from __future__ import annotations

from src.orchestration.code_debugging.schemas import (
    CodeDebuggingInput,
    ParsedDebuggingRequest,
)


def build_code_debugging_prompt(
    payload: CodeDebuggingInput,
    parsed: ParsedDebuggingRequest,
) -> str:
    """Build the compact fallback prompt."""
    return (
        "Fix the bug.\n"
        f"Language: {parsed.language}\n"
        f"Bug: {', '.join(parsed.bug_hints) or 'unknown'}\n"
        "Return corrected code only.\n"
        f"Code:\n{parsed.code.strip()}\n"
        f"Context: {payload.context.strip() if payload.context else 'none'}"
    )


def build_code_debugging_repair_prompt(
    payload: CodeDebuggingInput,
    parsed: ParsedDebuggingRequest,
    code: str,
    validation_errors: list[str],
) -> str:
    """Build a tiny repair prompt after validation fails."""
    errors = ", ".join(validation_errors) if validation_errors else "validation_failed"
    return (
        "Repair the code.\n"
        f"Language: {parsed.language}\n"
        f"Errors: {errors}\n"
        "Return corrected code only.\n"
        f"Code:\n{code.strip()}"
    )
