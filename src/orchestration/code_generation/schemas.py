"""Pydantic schemas for code generation."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.orchestration.factual_knowledge.schemas import (
    ExecutionTrace,
    Metadata,
    TokenUsage,
)


class LanguageSpec(BaseModel):
    """Detected programming language details."""

    language: str
    confidence: float = 0.0
    evidence: list[str] = Field(default_factory=list)
    formatter: str | None = None
    extensions: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class ComplexitySpec(BaseModel):
    """Estimated complexity for a code task."""

    level: str
    score: float = 0.0
    evidence: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class SpecSummary(BaseModel):
    """Structured task specification extracted from the request."""

    intent: str
    language: LanguageSpec
    complexity: ComplexitySpec
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class ValidationResult(BaseModel):
    """Result of deterministic code validation."""

    valid: bool
    formatted_code: str
    errors: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class CodeGenerationConfig(BaseModel):
    """Runtime knobs for code generation."""

    model: str | None = None
    max_tokens: int = 512
    temperature: float = 0.0
    top_p: float = 1.0
    repair_max_tokens: int = 256

    model_config = {"extra": "forbid"}


class CodeGenerationInput(BaseModel):
    """Code generation request payload."""

    request: str
    context: str | None = None
    preferred_language: str | None = None

    model_config = {"extra": "forbid"}


class CodeGenerationOutput(BaseModel):
    """Structured code generation result."""

    code: str
    formatted_code: str
    spec: SpecSummary
    validation: ValidationResult
    repaired: bool = False
    metadata: Metadata = Field(default_factory=Metadata)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    trace: list[ExecutionTrace] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}
