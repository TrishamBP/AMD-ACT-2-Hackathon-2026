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
_ONLY_CODE = "Return only code, no prose."

# One canonical template per category. Kept intentionally terse; the model's
# defaults handle the rest. `{prompt}` is the normalized, budgeted task text.
_TEMPLATES: dict[str, str] = {
    FACTUAL_KNOWLEDGE: "{prompt}\n\nAnswer directly in one sentence; no preamble.",
    MATHEMATICAL_REASONING: "{prompt}\n\nSolve concisely. " + _ANSWER_LINE,
    SENTIMENT_CLASSIFICATION: (
        "{prompt}\n\nReply with one word: Positive, Negative, Neutral, or Mixed."
    ),
    TEXT_SUMMARIZATION: "{prompt}\n\nSummarize per the constraints above. Do not restate the text.",
    NAMED_ENTITY_RECOGNITION: (
        "{prompt}\n\nList each entity and its type (Person, Organization, Location, "
        "Date), one per line. No other text."
    ),
    CODE_DEBUGGING: "{prompt}\n\nName the bug in one line, then give the fixed code. " + _ONLY_CODE,
    LOGICAL_REASONING: "{prompt}\n\nReason briefly. " + _ANSWER_LINE,
    CODE_GENERATION: "{prompt}\n\n" + _ONLY_CODE + " No comments or explanation unless asked.",
}

# Output ceilings. With REASONING_EFFORT=none the model answers directly (no
# chain-of-thought), so these only need to fit the actual answer plus a small
# safety margin. Sized from observed finish_reason=stop lengths per category.
_MAX_TOKENS: dict[str, int] = {
    FACTUAL_KNOWLEDGE: 128,
    MATHEMATICAL_REASONING: 256,
    SENTIMENT_CLASSIFICATION: 16,
    TEXT_SUMMARIZATION: 192,
    NAMED_ENTITY_RECOGNITION: 192,
    CODE_DEBUGGING: 384,
    LOGICAL_REASONING: 200,
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
