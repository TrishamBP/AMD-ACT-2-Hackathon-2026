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
    FACTUAL_KNOWLEDGE: "Answer the question factually and concisely.\n\n{prompt}",
    MATHEMATICAL_REASONING: "Solve the problem. Return the final answer only.\n\n{prompt}",
    SENTIMENT_CLASSIFICATION: (
        "Classify sentiment as positive, negative, or neutral. "
        "Return one label.\n\n{prompt}"
    ),
    TEXT_SUMMARIZATION: "Summarize in one sentence.\n\n{prompt}",
    NAMED_ENTITY_RECOGNITION: (
        "Extract entities as JSON with keys person, organization, "
        "location, date.\n\n{prompt}"
    ),
    CODE_DEBUGGING: "Find the bug, fix it, and return the corrected code.\n\n{prompt}",
    LOGICAL_REASONING: "Reason carefully and return the conclusion only.\n\n{prompt}",
    CODE_GENERATION: "Write correct code. Return code only.\n\n{prompt}",
}


def build_prompt(task: Task, routing_decision: RoutingDecision) -> str:
    """Build the final prompt for the selected handler."""
    template = _TEMPLATES[routing_decision.category]
    return template.format(prompt=task.prompt.strip())
