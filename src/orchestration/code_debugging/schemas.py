"""Pydantic schemas for code debugging."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.orchestration.factual_knowledge.schemas import (
    ExecutionTrace,
    Metadata,
    TokenUsage,
)


class CodeDebuggingConfig(BaseModel):
    """Runtime knobs for debugging."""

    model: str | None = None
    max_tokens: int = 256
    repair_max_tokens: int = 128
    temperature: float = 0.0
    top_p: float = 1.0
    confidence_threshold: float = 0.75

    model_config = {"extra": "forbid"}


class CodeDebuggingInput(BaseModel):
    """Debugging request payload."""

    request: str
    context: str | None = None
    preferred_language: str | None = None

    model_config = {"extra": "forbid"}


class ParsedDebuggingRequest(BaseModel):
    """Structured debugging request."""

    request: str
    language: str
    language_confidence: float = 0.0
    code: str = ""
    code_blocks: list[str] = Field(default_factory=list)
    syntax_valid: bool = False
    syntax_error: str | None = None
    ast_valid: bool = False
    lint_warnings: list[str] = Field(default_factory=list)
    static_findings: list[str] = Field(default_factory=list)
    bug_hints: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    line_count: int = 0

    model_config = {"extra": "forbid"}


class StaticAnalysisResult(BaseModel):
    """Static analysis findings for a code snippet."""

    valid: bool = True
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    evidence: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class BugDetectionResult(BaseModel):
    """Result from a bug detector."""

    detector_name: str
    bug_type: str
    confidence: float = 0.0
    evidence: list[str] = Field(default_factory=list)
    suggested_fix: str | None = None
    fixed_code: str | None = None
    solved: bool = False

    model_config = {"extra": "forbid"}


class ValidationResult(BaseModel):
    """Validation result for debugging output."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
    normalized_code: str = ""
    syntax_valid: bool = False
    lint_valid: bool = False
    static_valid: bool = False

    model_config = {"extra": "forbid"}


class DebuggingDecision(BaseModel):
    """Confidence aggregation result."""

    confidence: float = 0.0
    winner: BugDetectionResult | None = None
    evidence: list[str] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)
    solved: bool = False

    model_config = {"extra": "forbid"}


class CodeDebuggingOutput(BaseModel):
    """Structured debugging response."""

    code: str
    formatted_code: str
    parsed_request: ParsedDebuggingRequest
    analysis: list[BugDetectionResult] = Field(default_factory=list)
    static_analysis: StaticAnalysisResult = Field(default_factory=StaticAnalysisResult)
    decision: DebuggingDecision = Field(default_factory=DebuggingDecision)
    validation: ValidationResult
    metadata: Metadata = Field(default_factory=Metadata)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    trace: list[ExecutionTrace] = Field(default_factory=list)
    repaired: bool = False
    extra: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}
