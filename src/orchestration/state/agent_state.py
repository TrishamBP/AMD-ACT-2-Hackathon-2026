"""Shared typed state passed between LangGraph nodes."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.orchestration.factual_knowledge.schemas import ExecutionTrace, TokenUsage


class AgentState(BaseModel):
    """Shared state across the orchestration graph."""

    task_id: str
    original_prompt: str
    category: str | None = None
    confidence: float = 0.0
    selected_model: str | None = None
    selected_agent: str | None = None
    prompt_template: str | None = None
    available_tools: list[str] = Field(default_factory=list)
    llm_response: str | dict[str, Any] | None = None
    validated_response: dict[str, Any] | None = None
    execution_metadata: dict[str, Any] = Field(default_factory=dict)
    trace: list[ExecutionTrace] = Field(default_factory=list)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    errors: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}
