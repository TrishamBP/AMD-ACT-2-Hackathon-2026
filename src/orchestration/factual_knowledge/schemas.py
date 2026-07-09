"""Pydantic schemas for the factual knowledge agent."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    """Token accounting for a single node execution."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    model_config = {"extra": "forbid"}


class ExecutionTrace(BaseModel):
    """Structured execution trace entry."""

    node_name: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None
    latency_ms: float = 0.0
    retries: int = 0
    selected_model: str | None = None
    category: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    model_config = {"extra": "forbid"}


class Metadata(BaseModel):
    """Serializable execution metadata."""

    task_id: str | None = None
    node_name: str | None = None
    category: str | None = None
    selected_model: str | None = None
    selected_agent: str | None = None
    confidence: float | None = None
    evidence: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


class FactualKnowledgeConfig(BaseModel):
    """Runtime knobs for factual knowledge generation."""

    model: str | None = None
    max_tokens: int = 128
    temperature: float = 0.0
    top_p: float = 1.0

    model_config = {"extra": "forbid"}


class FactualKnowledgeInput(BaseModel):
    """Input payload for the factual knowledge agent."""

    question: str
    context: str | None = None
    allow_web_search: bool = False

    model_config = {"extra": "forbid"}


class FactualKnowledgeOutput(BaseModel):
    """Output payload for the factual knowledge agent."""

    answer: str
    confidence: float = 1.0
    uncertainty: str | None = None
    metadata: Metadata = Field(default_factory=Metadata)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    trace: list[ExecutionTrace] = Field(default_factory=list)

    model_config = {"extra": "forbid"}
