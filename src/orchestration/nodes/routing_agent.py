"""Deterministic routing agent node."""
from __future__ import annotations

from dataclasses import dataclass
import logging
import re
from typing import Final

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
from src.orchestration.logging import log_node_event
from src.orchestration.state.agent_state import AgentState
from src.orchestration.tracing import track_tokens, trace_node

_CATEGORY_AGENT_MAP: Final[dict[str, str]] = {
    FACTUAL_KNOWLEDGE: "FactualKnowledgeAgent",
    MATHEMATICAL_REASONING: "MathematicalReasoningAgent",
    SENTIMENT_CLASSIFICATION: "SentimentClassificationAgent",
    TEXT_SUMMARIZATION: "TextSummarizationAgent",
    NAMED_ENTITY_RECOGNITION: "NamedEntityRecognitionAgent",
    CODE_DEBUGGING: "CodeDebuggingAgent",
    LOGICAL_REASONING: "LogicalReasoningAgent",
    CODE_GENERATION: "CodeGenerationAgent",
}


@dataclass(slots=True)
class RoutingAgent:
    """Deterministic heuristic router."""

    threshold: float = 0.65
    logger: logging.Logger = logging.getLogger("src.orchestration.routing")

    def _score(self, prompt: str) -> tuple[dict[str, float], dict[str, list[str]]]:
        text = prompt.lower()
        scores = {category: 0.0 for category in _CATEGORY_AGENT_MAP}
        evidence = {category: [] for category in _CATEGORY_AGENT_MAP}

        def add(category: str, amount: float, reason: str) -> None:
            scores[category] = min(1.0, scores[category] + amount)
            evidence[category].append(reason)

        factual_signals = {
            "what is": 0.28,
            "define": 0.25,
            "explain": 0.22,
            "how does": 0.20,
            "why does": 0.20,
            "describe": 0.16,
        }
        summarization_signals = {
            "summarize": 0.40,
            "summary": 0.35,
            "one sentence": 0.25,
            "concise": 0.15,
        }
        ner_signals = {
            "extract entities": 0.35,
            "named entities": 0.30,
            "list all": 0.15,
            "person": 0.10,
            "organization": 0.10,
            "location": 0.10,
            "date": 0.10,
        }
        sentiment_signals = {
            "sentiment": 0.35,
            "positive": 0.20,
            "negative": 0.20,
            "neutral": 0.20,
        }
        math_signals = {
            "solve": 0.25,
            "calculate": 0.25,
            "compute": 0.25,
            "+": 0.10,
            "-": 0.10,
            "*": 0.10,
            "/": 0.10,
        }
        debugging_signals = {
            "fix": 0.30,
            "bug": 0.25,
            "debug": 0.25,
            "traceback": 0.25,
            "error": 0.20,
        }
        codegen_signals = {
            "write code": 0.30,
            "implement": 0.25,
            "function": 0.15,
            "class": 0.15,
            "python": 0.15,
        }
        logic_signals = {
            "logic": 0.25,
            "deduce": 0.20,
            "infer": 0.18,
            "therefore": 0.15,
            "which of": 0.20,
        }

        for phrase, weight in factual_signals.items():
            if phrase in text:
                add(FACTUAL_KNOWLEDGE, weight, f"matched factual phrase: {phrase}")
        for phrase, weight in summarization_signals.items():
            if phrase in text:
                add(TEXT_SUMMARIZATION, weight, f"matched summarization phrase: {phrase}")
        for phrase, weight in ner_signals.items():
            if phrase in text:
                add(NAMED_ENTITY_RECOGNITION, weight, f"matched ner phrase: {phrase}")
        for phrase, weight in sentiment_signals.items():
            if phrase in text:
                add(SENTIMENT_CLASSIFICATION, weight, f"matched sentiment phrase: {phrase}")
        for phrase, weight in math_signals.items():
            if phrase in text:
                add(MATHEMATICAL_REASONING, weight, f"matched math signal: {phrase}")
        for phrase, weight in debugging_signals.items():
            if phrase in text:
                add(CODE_DEBUGGING, weight, f"matched debugging phrase: {phrase}")
        for phrase, weight in codegen_signals.items():
            if phrase in text:
                add(CODE_GENERATION, weight, f"matched codegen phrase: {phrase}")
        for phrase, weight in logic_signals.items():
            if phrase in text:
                add(LOGICAL_REASONING, weight, f"matched logic phrase: {phrase}")

        if "```" in prompt:
            add(CODE_DEBUGGING, 0.25, "contains code fence")
            add(CODE_GENERATION, 0.20, "contains code fence")
        if len(prompt) > 300:
            add(TEXT_SUMMARIZATION, 0.15, "contains long paragraph")
        if re.search(r"\b\d+\b", text):
            add(MATHEMATICAL_REASONING, 0.12, "contains numbers")

        return scores, evidence

    def _route(self, prompt: str) -> tuple[str, float, list[str]]:
        scores, evidence = self._score(prompt)
        ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        winner, confidence = ordered[0]
        reasons = evidence[winner]
        return winner, confidence, reasons

    @trace_node("RoutingAgent")
    @track_tokens
    async def __call__(self, state: AgentState) -> AgentState:
        """Route a task deterministically."""
        category, confidence, evidence = self._route(state.original_prompt)
        selected_agent = _CATEGORY_AGENT_MAP[category]
        log_node_event(
            "routing_decision",
            task_id=state.task_id,
            node="RoutingAgent",
            category=category,
            confidence=confidence,
            selected_agent=selected_agent,
        )
        return state.model_copy(
            update={
                "category": category,
                "confidence": confidence,
                "selected_agent": selected_agent,
                "execution_metadata": {
                    **state.execution_metadata,
                    "routing_evidence": evidence,
                },
            }
        )
