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
    FACTUAL_KNOWLEDGE: (
        "{prompt}\n\n"
        "Give a clear, direct answer. Be concise but complete."
    ),
    MATHEMATICAL_REASONING: (
        "{prompt}\n\n"
        "Solve step by step, then clearly state the final answer."
    ),
    SENTIMENT_CLASSIFICATION: (
        "{prompt}\n\n"
        "Classify the sentiment and briefly justify your classification."
    ),
    TEXT_SUMMARIZATION: (
        "{prompt}\n\n"
        "Provide a concise summary following any length/format constraints given above."
    ),
    NAMED_ENTITY_RECOGNITION: (
        "{prompt}\n\n"
        "List each entity with its type (Person, Organization, Location, Date, etc.)."
    ),
    CODE_DEBUGGING: (
        "{prompt}\n\n"
        "Identify the bug, explain it briefly, then provide the corrected code."
    ),
    LOGICAL_REASONING: (
        "{prompt}\n\n"
        "Reason through this step by step, then clearly state your final answer."
    ),
    CODE_GENERATION: (
        "{prompt}\n\n"
        "Write the complete, working code."
    ),
}


def build_prompt(task: Task, routing_decision: RoutingDecision) -> str:
    """Build the final prompt for the selected handler."""
    template = _TEMPLATES[routing_decision.category]
    return template.format(prompt=task.prompt.strip())
