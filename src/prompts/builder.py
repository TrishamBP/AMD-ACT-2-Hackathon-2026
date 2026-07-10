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
    MATHEMATICAL_REASONING: (
        "Solve this step by step:\n\n"
        "{prompt}\n\n"
        "Show your work, then state the final answer as a number."
    ),
    SENTIMENT_CLASSIFICATION: (
        "Classify the overall sentiment as: positive, negative, or mixed.\n\n"
        "{prompt}\n\n"
        "Answer with one word only."
    ),
    TEXT_SUMMARIZATION: (
        "Read the following text and summarize it in exactly one sentence. "
        "Include the main topics and key points.\n\n"
        "{prompt}"
    ),
    NAMED_ENTITY_RECOGNITION: (
        "Extract ALL named entities from the text below. "
        "For each entity, identify its type (PERSON, ORGANIZATION, LOCATION, DATE, etc.).\n\n"
        "Text: {prompt}\n\n"
        "Format:\n"
        "- Entity name: Type"
    ),
    CODE_DEBUGGING: (
        "The code below has a bug. Identify the bug and provide the corrected code.\n\n"
        "{prompt}\n\n"
        "Return only the fixed code."
    ),
    LOGICAL_REASONING: (
        "Solve this logic puzzle step by step:\n\n"
        "{prompt}\n\n"
        "State your reasoning, then give the final answer."
    ),
    CODE_GENERATION: (
        "Write a Python function that:\n\n"
        "{prompt}\n\n"
        "Return only the complete, working code."
    ),
}


def build_prompt(task: Task, routing_decision: RoutingDecision) -> str:
    """Build the final prompt for the selected handler."""
    template = _TEMPLATES[routing_decision.category]
    return template.format(prompt=task.prompt.strip())
