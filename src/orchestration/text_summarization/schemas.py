"""Pydantic schemas for text summarization."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    """Token accounting for summarization."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    model_config = {"extra": "forbid"}


class SummaryConstraints(BaseModel):
    """Structured summarization constraints."""

    length_type: str = "free"
    target_words: int | None = None
    target_sentences: int | None = None
    output_format: str = "plain"
    bullet_count: int | None = None
    paragraph_count: int | None = None
    preserve_language: bool = True
    evidence: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class DocumentProfile(BaseModel):
    """Deterministic analysis of the source document."""

    word_count: int = 0
    sentence_count: int = 0
    paragraph_count: int = 0
    char_count: int = 0
    estimated_language: str = "unknown"
    estimated_size: str = "short"
    duplicate_blank_lines_removed: int = 0
    normalized_text: str = ""

    model_config = {"extra": "forbid"}


class SummaryRequest(BaseModel):
    """Input payload for summarization."""

    text: str
    context: str | None = None
    preferred_language: str | None = None
    preferred_format: str | None = None

    model_config = {"extra": "forbid"}


class SummaryValidation(BaseModel):
    """Validation result for generated summaries."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
    word_count: int = 0
    sentence_count: int = 0
    bullet_count: int = 0
    paragraph_count: int = 0
    is_json: bool = False

    model_config = {"extra": "forbid"}


class ExecutionMetadata(BaseModel):
    """Serializable execution metadata for summarization."""

    task_id: str | None = None
    node_name: str | None = None
    selected_model: str | None = None
    repair_attempts: int = 0
    summary_length: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


class SummaryResponse(BaseModel):
    """Summarization output."""

    summary: str
    constraints: SummaryConstraints = Field(default_factory=SummaryConstraints)
    validation: SummaryValidation = Field(default_factory=lambda: SummaryValidation(valid=True))
    metadata: ExecutionMetadata = Field(default_factory=ExecutionMetadata)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    trace: list[dict[str, Any]] = Field(default_factory=list)
    repaired: bool = False
    extra: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}
