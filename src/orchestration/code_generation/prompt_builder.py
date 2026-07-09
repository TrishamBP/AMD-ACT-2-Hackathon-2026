"""Compact prompt builder for code generation."""
from __future__ import annotations

from src.orchestration.code_generation.schemas import CodeGenerationInput, SpecSummary


def _render_spec(spec: SpecSummary) -> str:
    inputs = ", ".join(spec.inputs) if spec.inputs else "unspecified"
    outputs = ", ".join(spec.outputs) if spec.outputs else "unspecified"
    constraints = ", ".join(spec.constraints) if spec.constraints else "none"
    return (
        f"language={spec.language.language}; "
        f"complexity={spec.complexity.level}; "
        f"inputs={inputs}; outputs={outputs}; constraints={constraints}"
    )


def build_code_generation_prompt(payload: CodeGenerationInput, spec: SpecSummary) -> str:
    """Build the single-shot generation prompt."""
    context = payload.context.strip() if payload.context else "none"
    return (
        f"You are an expert {spec.language.language} engineer.\n"
        f"Return only code.\n"
        f"Task: {payload.request.strip()}\n"
        f"Spec: {_render_spec(spec)}\n"
        f"Context: {context}\n"
        f"Constraints: {', '.join(spec.constraints) if spec.constraints else 'none'}"
    )


def build_code_repair_prompt(
    payload: CodeGenerationInput,
    spec: SpecSummary,
    invalid_code: str,
    validation_errors: list[str],
) -> str:
    """Build a tiny repair prompt after validation fails."""
    errors = ", ".join(validation_errors) if validation_errors else "validation_failed"
    return (
        f"Fix the {spec.language.language} code.\n"
        f"Return only corrected code.\n"
        f"Task: {payload.request.strip()}\n"
        f"Errors: {errors}\n"
        f"Code:\n{invalid_code.strip()}"
    )
