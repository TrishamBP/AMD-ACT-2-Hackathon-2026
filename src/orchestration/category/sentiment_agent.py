"""Sentiment classification with deterministic handler."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol

from src.orchestration.cache.answer_cache import AnswerCache
from src.orchestration.compression.compressor import PromptCompressor
from src.orchestration.deterministic.sentiment import SentimentDeterministicHandler
from src.orchestration.logging import log_node_event
from src.orchestration.state.agent_state import AgentState
from src.orchestration.tracing import track_tokens, trace_node


class SentimentClient(Protocol):
    """Injected model client contract."""

    async def generate(
        self,
        prompt: str,
        *,
        model: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
    ) -> str:
        """Generate sentiment output."""


@dataclass(slots=True)
class SentimentClassificationAgent:
    """Sentiment classification with aggressive token reduction."""

    client: SentimentClient | None = None
    cache: AnswerCache = field(default_factory=AnswerCache)
    deterministic_handler: SentimentDeterministicHandler = field(
        default_factory=SentimentDeterministicHandler
    )
    compressor: PromptCompressor = field(default_factory=PromptCompressor)
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("src.orchestration.sentiment")
    )
    selected_model: str | None = None
    max_tokens: int = 8
    temperature: float = 0.0
    top_p: float = 1.0

    @trace_node("SentimentClassificationAgent")
    @track_tokens
    async def __call__(self, state: AgentState) -> AgentState:
        """Classify sentiment with deterministic-first approach."""
        prompt = state.original_prompt

        cached = self.cache.get(prompt)
        if cached:
            log_node_event(
                "sentiment_cache_hit",
                task_id=state.task_id,
                node="SentimentClassificationAgent",
                method="cache",
            )
            return state.model_copy(
                update={
                    "llm_response": cached.answer,
                    "validated_response": {"answer": cached.answer},
                }
            )

        if self.deterministic_handler.can_solve(prompt):
            solved, answer, confidence, method = self.deterministic_handler.solve(prompt)
            if solved and confidence >= 0.85:
                self.cache.set(prompt, answer, confidence, method, "sentiment")
                log_node_event(
                    "sentiment_deterministic",
                    task_id=state.task_id,
                    node="SentimentClassificationAgent",
                    method=method,
                    confidence=confidence,
                )
                return state.model_copy(
                    update={
                        "llm_response": answer,
                        "validated_response": {"answer": answer},
                    }
                )

        if self.client is None:
            return state.model_copy(
                update={"errors": [*state.errors, "sentiment_client_not_configured"]}
            )

        model = state.selected_model or self.selected_model
        if model is None:
            return state.model_copy(update={"errors": [*state.errors, "model_not_selected"]})

        compressed_prompt = self.compressor.compress_sentiment(prompt)
        raw_response = await self.client.generate(
            compressed_prompt,
            model=model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
        )

        answer = raw_response.strip()
        self.cache.set(prompt, answer, 0.90, "llm_compressed", "sentiment")

        log_node_event(
            "sentiment_llm_fallback",
            task_id=state.task_id,
            node="SentimentClassificationAgent",
            model=model,
        )

        return state.model_copy(
            update={
                "llm_response": answer,
                "validated_response": {"answer": answer},
            }
        )
