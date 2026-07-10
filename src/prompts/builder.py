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
    FACTUAL_KNOWLEDGE: "Answer concisely.\n\n{prompt}",
    MATHEMATICAL_REASONING: (
        "{prompt}\n\n"
        "Show each calculation step briefly, then on the last line write only the final number."
    ),
    SENTIMENT_CLASSIFICATION: (
        "{prompt}\n\n"
        "Answer: positive, negative, or mixed"
    ),
    TEXT_SUMMARIZATION: (
        "{prompt}\n\n"
        "Summarize in one sentence."
    ),
    NAMED_ENTITY_RECOGNITION: (
        "{prompt}\n\n"
        "Extract entities:\n- Name: Type"
    ),
    CODE_DEBUGGING: (
        "{prompt}\n\n"
        "Fixed code:"
    ),
    LOGICAL_REASONING: (
        "{prompt}\n\n"
        "Work through each constraint one by one:\n"
        "1. List all constraints from the problem.\n"
        "2. Apply each constraint to eliminate possibilities.\n"
        "3. State the final answer clearly."
    ),
    CODE_GENERATION: (
        "{prompt}\n\n"
        "```python\n"
    ),
}


def build_prompt(task: Task, routing_decision: RoutingDecision) -> str:
    """Build the final prompt for the selected handler."""
    template = _TEMPLATES[routing_decision.category]
    return template.format(prompt=task.prompt.strip())
