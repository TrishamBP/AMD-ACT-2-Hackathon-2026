"""Prompt assembly for task-specific handlers."""
from __future__ import annotations

from src.config.constants import (
    CODE_DEBUGGING,
    CODE_GENERATION,
    FACTUAL_KNOWLEDGE,
    LOGICAL_REASONING,
    MATHEMATICAL_REASONING,
    NAMED_ENTITY_RECOGNITION,
    SENTIMENT_CLASSIFICATION,
    TEXT_SUMMARIZATION,
)
from src.models.task import Task
from src.routing.router import RoutingDecision

_TEMPLATES: dict[str, str] = {
    FACTUAL_KNOWLEDGE: "{prompt}\nAnswer:",
    MATHEMATICAL_REASONING: "{prompt}\nSolve, then state the final answer.",
    SENTIMENT_CLASSIFICATION: "{prompt}\nSentiment:",
    TEXT_SUMMARIZATION: "{prompt}\nSummary:",
    NAMED_ENTITY_RECOGNITION: "{prompt}\nEntities:",
    CODE_DEBUGGING: "{prompt}\nBug and fix:",
    LOGICAL_REASONING: "{prompt}\nReason step by step. Answer:",
    CODE_GENERATION: "{prompt}",
}

_MAX_TOKENS: dict[str, int] = {
    FACTUAL_KNOWLEDGE: 150,
    MATHEMATICAL_REASONING: 200,
    SENTIMENT_CLASSIFICATION: 30,
    TEXT_SUMMARIZATION: 150,
    NAMED_ENTITY_RECOGNITION: 100,
    CODE_DEBUGGING: 256,
    LOGICAL_REASONING: 150,
    CODE_GENERATION: 300,
}


def get_max_tokens(category: str) -> int:
    """Get max tokens for a category."""
    return _MAX_TOKENS.get(category, 256)


def build_prompt(task: Task, routing_decision: RoutingDecision) -> str:
    """Build the final prompt for the selected handler."""
    template = _TEMPLATES[routing_decision.category]
    return template.format(prompt=task.prompt.strip())
