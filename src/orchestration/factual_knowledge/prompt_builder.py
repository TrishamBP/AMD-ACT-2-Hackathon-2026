"""Compact prompt builder for factual knowledge tasks."""
from __future__ import annotations

from src.orchestration.factual_knowledge.schemas import FactualKnowledgeInput

_FACTUAL_PROMPT_TEMPLATE = """Answer the question factually and concisely.
If unsure, say "I don't know".

Example:
Q: What is TCP/IP?
A: TCP/IP is the internet protocol suite used for communication on networks.

Question: {question}
Context: {context}
A:"""


def build_factual_prompt(payload: FactualKnowledgeInput) -> str:
    """Build the compact factual knowledge prompt."""
    context = payload.context.strip() if payload.context else "None"
    return _FACTUAL_PROMPT_TEMPLATE.format(
        question=payload.question.strip(),
        context=context,
    )


def factual_prompt_template() -> str:
    """Return the reusable factual prompt template."""
    return _FACTUAL_PROMPT_TEMPLATE
