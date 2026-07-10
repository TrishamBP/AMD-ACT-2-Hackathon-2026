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
    FACTUAL_KNOWLEDGE: "{prompt}\n\nAnswer briefly.",
    MATHEMATICAL_REASONING: "{prompt}\n\nSolve. Final line: just the number.",
    SENTIMENT_CLASSIFICATION: "{prompt}\n\nSentiment (one word):",
    TEXT_SUMMARIZATION: "{prompt}\n\nOne sentence summary:",
    NAMED_ENTITY_RECOGNITION: "{prompt}\n\nEntities (Name: Type):",
    CODE_DEBUGGING: "{prompt}\n\nFixed code:",
    LOGICAL_REASONING: "{prompt}\n\nApply each constraint, then state the answer.",
    CODE_GENERATION: "{prompt}\n\n```python\n",
}


def build_prompt(task: Task, routing_decision: RoutingDecision) -> str:
    """Build the final prompt for the selected handler."""
    template = _TEMPLATES[routing_decision.category]
    return template.format(prompt=task.prompt.strip())
