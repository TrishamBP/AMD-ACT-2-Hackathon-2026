"""Prompt assembly for task-specific handlers.

Design goals (enforced here):
- One canonical, ultra-compact template per category.
- Explicit output-length caps live in the template (cheap output tokens).
- Input is normalized and budgeted before templating (cheap input tokens).
- Shared instruction fragments avoid duplication/drift across categories.
"""
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
from src.prompts.normalize import prepare_input
from src.routing.router import RoutingDecision

# Shared fragments: change once, every category using it gets cheaper.
_ANSWER_LINE = "End with a line 'Answer: <final answer>'."

# One canonical template per category. Kept intentionally terse; the model's
# defaults handle the rest. `{prompt}` is the normalized, budgeted task text.
#
# Templates are MIS-ROUTE TOLERANT: the router is imperfect on adversarial
# inputs, so category-specific formatting is phrased conditionally ("if this
# is X, do Y; otherwise answer directly"). A mis-routed task then still gets a
# correct answer instead of being forced into a broken format.
_TEMPLATES: dict[str, str] = {
    FACTUAL_KNOWLEDGE: "{prompt}\n\nAnswer directly and concisely; no preamble.",
    MATHEMATICAL_REASONING: "{prompt}\n\nSolve concisely. " + _ANSWER_LINE,
    SENTIMENT_CLASSIFICATION: (
        "{prompt}\n\nIf this asks for sentiment/tone, reply with one word "
        "(Positive, Negative, Neutral, or Mixed); otherwise answer directly."
    ),
    TEXT_SUMMARIZATION: (
        "{prompt}\n\nIf asked to summarize, summarize per the constraints and do "
        "not restate the text; otherwise answer directly."
    ),
    NAMED_ENTITY_RECOGNITION: (
        "{prompt}\n\nIf asked to extract entities, list each entity and its type "
        "(Person, Organization, Location, Date), one per line; otherwise answer "
        "directly."
    ),
    CODE_DEBUGGING: (
        "{prompt}\n\nIf this is a coding task, name the bug in one line then give "
        "the fixed code and nothing else; otherwise answer directly."
    ),
    LOGICAL_REASONING: "{prompt}\n\nReason briefly. " + _ANSWER_LINE,
    CODE_GENERATION: (
        "{prompt}\n\nIf this is a coding task, return only the code (no comments "
        "or explanation unless asked); otherwise answer directly."
    ),
}

# Output ceilings. With REASONING_EFFORT=none the model answers directly (no
# chain-of-thought), so these only need to fit the actual answer plus a safety
# margin. NOTE: max_tokens is a CEILING, not a target -- a correctly-routed
# task still stops early (e.g. one-word sentiment ~2 tokens), so these margins
# are free and exist purely to protect MIS-ROUTED tasks from truncation.
_MAX_TOKENS: dict[str, int] = {
    FACTUAL_KNOWLEDGE: 200,
    MATHEMATICAL_REASONING: 256,
    SENTIMENT_CLASSIFICATION: 96,
    TEXT_SUMMARIZATION: 224,
    NAMED_ENTITY_RECOGNITION: 224,
    CODE_DEBUGGING: 384,
    LOGICAL_REASONING: 224,
    CODE_GENERATION: 384,
}


def get_max_tokens(category: str) -> int:
    """Get max output tokens for a category."""
    return _MAX_TOKENS.get(category, 256)


def build_prompt(task: Task, routing_decision: RoutingDecision) -> str:
    """Build the final prompt: normalize + budget input, then apply template."""
    category = routing_decision.category
    template = _TEMPLATES[category]
    prepared = prepare_input(task.prompt, category)
    return template.format(prompt=prepared)
