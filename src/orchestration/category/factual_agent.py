"""Factual knowledge agent node."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

from src.orchestration.cache.answer_cache import AnswerCache
from src.orchestration.compression.compressor import PromptCompressor
from src.orchestration.factual_knowledge.guardrails import FactualKnowledgeGuardrails
from src.orchestration.factual_knowledge.prompt_builder import (
    build_factual_prompt,
    factual_prompt_template,
)
from src.orchestration.factual_knowledge.schemas import (
    FactualKnowledgeConfig,
    FactualKnowledgeInput,
    FactualKnowledgeOutput,
    Metadata,
    TokenUsage,
)
from src.orchestration.logging import log_node_event
from src.orchestration.state.agent_state import AgentState
from src.orchestration.tracing import track_tokens, trace_node
from src.orchestration.validators.response_validator import ResponseValidator


class FactualKnowledgeClient(Protocol):
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
        """Generate factual knowledge output."""


class WebSearchTool(Protocol):
    """Optional web search contract."""

    name: str
    description: str

    async def arun(self, query: str) -> str:
        """Execute a web search."""


@dataclass(slots=True)
class FactualKnowledgeAgent:
    """Factual knowledge category node."""

    client: FactualKnowledgeClient | None = None
    cache: AnswerCache = field(default_factory=AnswerCache)
    compressor: PromptCompressor = field(default_factory=PromptCompressor)
    web_search_tool: WebSearchTool | None = None
    guardrails: FactualKnowledgeGuardrails = field(default_factory=FactualKnowledgeGuardrails)
    validator: ResponseValidator = field(default_factory=ResponseValidator)
    config: FactualKnowledgeConfig = field(default_factory=FactualKnowledgeConfig)
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("src.orchestration.factual_knowledge")
    )

    @property
    def tool_names(self) -> list[str]:
        """Return available tool names without executing them."""
        if self.web_search_tool is None:
            return []
        return [self.web_search_tool.name]

    def _build_input(self, state: AgentState) -> FactualKnowledgeInput:
        return FactualKnowledgeInput(
            question=state.original_prompt,
            context=state.execution_metadata.get("context"),
            allow_web_search=bool(self.web_search_tool),
        )

    def _seed_state(self, state: AgentState, prompt: str) -> AgentState:
        metadata = Metadata(
            task_id=state.task_id,
            node_name="FactualKnowledgeAgent",
            category="factual_knowledge",
            selected_model=state.selected_model or self.config.model,
            selected_agent="FactualKnowledgeAgent",
            tools=self.tool_names,
            extra={"prompt_length": len(prompt)},
        )
        return state.model_copy(
            update={
                "category": "factual_knowledge",
                "selected_agent": "FactualKnowledgeAgent",
                "prompt_template": factual_prompt_template(),
                "available_tools": self.tool_names,
                "execution_metadata": {
                    **state.execution_metadata,
                    "factual_metadata": metadata.model_dump(),
                },
            }
        )

    async def _call_client(self, prompt: str, model: str) -> str:
        if self.client is None:
            return ""
        return await self.client.generate(
            prompt,
            model=model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
        )

    @trace_node("FactualKnowledgeAgent")
    @track_tokens
    async def __call__(self, state: AgentState) -> AgentState:
        """Process a factual knowledge task."""
        prompt_text = state.original_prompt

        cached = self.cache.get(prompt_text)
        if cached:
            log_node_event(
                "factual_cache_hit",
                task_id=state.task_id,
                node="FactualKnowledgeAgent",
                method="cache",
            )
            return state.model_copy(
                update={
                    "llm_response": cached.answer,
                    "validated_response": {"answer": cached.answer},
                }
            )

        factual_input = self.guardrails.validate_input(self._build_input(state))
        compressed_prompt = self.compressor.compress_factual(factual_input.question)
        working_state = self._seed_state(state, compressed_prompt)

        if self.client is None:
            return working_state.model_copy(
                update={"errors": [*working_state.errors, "factual_model_client_not_configured"]}
            )

        model = working_state.selected_model or self.config.model
        if model is None:
            return working_state.model_copy(
                update={"errors": [*working_state.errors, "selected_model_missing"]}
            )

        raw_response = await self._call_client(compressed_prompt, model)
        answer = raw_response.strip()

        self.cache.set(prompt_text, answer, 0.90, "llm_compressed", "factual_knowledge")

        structured = FactualKnowledgeOutput(
            answer=answer,
            confidence=1.0,
            metadata=Metadata(
                task_id=state.task_id,
                node_name="FactualKnowledgeAgent",
                category="factual_knowledge",
                selected_model=model,
                selected_agent="FactualKnowledgeAgent",
                tools=self.tool_names,
            ),
            token_usage=TokenUsage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
            ),
        )
        validated_output = self.guardrails.validate_output(structured)
        log_node_event(
            "factual_output_validated",
            task_id=state.task_id,
            node="FactualKnowledgeAgent",
            category="factual_knowledge",
            selected_model=model,
        )
        return working_state.model_copy(
            update={
                "llm_response": answer,
                "validated_response": validated_output.model_dump(),
                "token_usage": validated_output.token_usage,
            }
        )
