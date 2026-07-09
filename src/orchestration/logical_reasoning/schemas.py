"""Pydantic schemas for logical reasoning."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from src.orchestration.factual_knowledge.schemas import (
    ExecutionTrace,
    Metadata,
    TokenUsage,
)


class LogicalReasoningConfig(BaseModel):
    """Runtime knobs for logical reasoning."""

    model: str | None = None
    max_tokens: int = 192
    repair_max_tokens: int = 96
    temperature: float = 0.0
    top_p: float = 1.0
    confidence_threshold: float = 0.75

    model_config = {"extra": "forbid"}


class LogicalReasoningInput(BaseModel):
    """Input payload for logical reasoning."""

    request: str
    context: str | None = None
    preferred_format: str | None = None

    model_config = {"extra": "forbid"}


class ConstraintExtractionResult(BaseModel):
    """Structured logical constraints."""

    variables: list[str] = Field(default_factory=list)
    relationships: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    rules: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    objectives: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class ParsedLogicalProblem(BaseModel):
    """Logical reasoning problem with extracted structure."""

    request: str
    reasoning_type: str
    confidence: float = 0.0
    evidence: list[str] = Field(default_factory=list)
    code: str = ""
    statements: list[str] = Field(default_factory=list)
    rules: list[str] = Field(default_factory=list)
    variables: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    objectives: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    relationships: list[str] = Field(default_factory=list)
    normalized_clauses: list[str] = Field(default_factory=list)
    line_count: int = 0

    model_config = {"extra": "forbid"}


class ReasoningSolution(BaseModel):
    """Result from a reasoning solver."""

    solver_name: str
    reasoning_type: str
    result: str
    confidence: float = 0.0
    evidence: list[str] = Field(default_factory=list)
    solved: bool = False

    model_config = {"extra": "forbid"}


class ReasoningDecision(BaseModel):
    """Aggregated reasoning confidence."""

    confidence: float = 0.0
    winner: ReasoningSolution | None = None
    evidence: list[str] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)
    solved: bool = False

    model_config = {"extra": "forbid"}


class ValidationResult(BaseModel):
    """Validation result for reasoning output."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
    normalized_answer: str = ""
    consistent: bool = False
    constraint_satisfied: bool = False

    model_config = {"extra": "forbid"}


class ExecutionMetadata(BaseModel):
    """Serializable execution metadata for reasoning tasks."""

    task_id: str | None = None
    node_name: str | None = None
    reasoning_type: str | None = None
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


class LogicalReasoningOutput(BaseModel):
    """Final logical reasoning response."""

    answer: str
    parsed_problem: ParsedLogicalProblem
    solution: ReasoningSolution | None = None
    decision: ReasoningDecision = Field(default_factory=ReasoningDecision)
    validation: ValidationResult = Field(default_factory=lambda: ValidationResult(valid=True))
    metadata: Metadata = Field(default_factory=Metadata)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    trace: list[ExecutionTrace] = Field(default_factory=list)
    repaired: bool = False
    extra: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}
