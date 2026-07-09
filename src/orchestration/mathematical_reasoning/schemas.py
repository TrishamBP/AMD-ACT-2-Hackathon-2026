"""Pydantic schemas for mathematical reasoning."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    """Token accounting for math tasks."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    model_config = {"extra": "forbid"}


class MathProblem(BaseModel):
    """Input payload for math reasoning."""

    statement: str
    context: str | None = None
    preferred_units: str | None = None

    model_config = {"extra": "forbid"}


class ParsedProblem(BaseModel):
    """Structured math problem representation."""

    problem_type: str
    confidence: float = 0.0
    evidence: list[str] = Field(default_factory=list)
    statement: str = ""
    numbers: list[float] = Field(default_factory=list)
    variables: list[str] = Field(default_factory=list)
    operators: list[str] = Field(default_factory=list)
    equations: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    units: list[str] = Field(default_factory=list)
    requested_outputs: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class SolverResult(BaseModel):
    """Result from a deterministic solver."""

    solver_name: str
    problem_type: str
    result: str
    confidence: float = 0.0
    evidence: list[str] = Field(default_factory=list)
    solved: bool = False

    model_config = {"extra": "forbid"}


class ValidationResult(BaseModel):
    """Validation result for math output."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
    normalized_answer: str = ""
    numeric_value: float | None = None
    units: str | None = None
    is_equation: bool = False

    model_config = {"extra": "forbid"}


class ExecutionMetadata(BaseModel):
    """Serializable execution metadata for math tasks."""

    task_id: str | None = None
    node_name: str | None = None
    problem_type: str | None = None
    selected_solver: str | None = None
    solver_confidence: float = 0.0
    fallback_used: bool = False
    repair_attempts: int = 0
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


class MathResponse(BaseModel):
    """Final math response."""

    answer: str
    parsed_problem: ParsedProblem
    solver_result: SolverResult | None = None
    validation: ValidationResult = Field(default_factory=lambda: ValidationResult(valid=True))
    metadata: ExecutionMetadata = Field(default_factory=ExecutionMetadata)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    trace: list[dict[str, Any]] = Field(default_factory=list)
    repaired: bool = False
    extra: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}
