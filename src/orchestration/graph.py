"""LangGraph-compatible orchestration graph."""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

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
from src.orchestration.category import (
    CodeDebuggingAgent,
    CodeGenerationAgent,
    FactualKnowledgeAgent,
    LogicalReasoningAgent,
    MathematicalReasoningAgent,
    NamedEntityRecognitionAgent,
    SentimentClassificationAgent,
    TextSummarizationAgent,
)
from src.orchestration.nodes.routing_agent import RoutingAgent
from src.orchestration.nodes.validator import ValidatorNode
from src.orchestration.state.agent_state import AgentState

NodeCallable = Callable[[AgentState], Awaitable[AgentState] | AgentState]

try:  # pragma: no cover - optional dependency
    from langgraph.graph import END, START, StateGraph

    _HAS_LANGGRAPH = True
except ImportError:  # pragma: no cover - fallback for local development
    END = "__end__"
    START = "__start__"
    _HAS_LANGGRAPH = False

    class StateGraph:  # type: ignore[override]
        """Minimal LangGraph fallback used when the dependency is unavailable."""

        def __init__(self, state_type: type[AgentState]) -> None:
            self._state_type = state_type
            self._nodes: dict[str, NodeCallable] = {}
            self._start: str | None = None
            self._routing_node: str | None = None
            self._category_nodes: dict[str, str] = {}
            self._validator_node: str | None = None

        def add_node(
            self,
            name: str,
            node: NodeCallable,
        ) -> None:
            self._nodes[name] = node

        def add_edge(self, source: str, target: str) -> None:
            if source == START:
                self._start = target
            elif target == END:
                self._validator_node = source

        def add_conditional_edges(
            self,
            source: str,
            selector: Callable[[AgentState], str],
            mapping: dict[str, str],
        ) -> None:
            self._routing_node = source
            self._category_nodes = mapping
            self._selector = selector

        def compile(self) -> "_CompiledGraph":
            return _CompiledGraph(
                nodes=self._nodes,
                start=self._start or "",
                routing_node=self._routing_node or "",
                selector=getattr(self, "_selector", lambda state: state.selected_agent or ""),
                category_nodes=self._category_nodes,
                validator_node=self._validator_node or "",
            )


@dataclass(slots=True)
class _CompiledGraph:
    """Fallback compiled graph that executes the registered nodes in order."""

    nodes: dict[str, NodeCallable]
    start: str
    routing_node: str
    selector: Callable[[AgentState], str]
    category_nodes: dict[str, str]
    validator_node: str

    async def _call(self, node_name: str, state: AgentState) -> AgentState:
        node = self.nodes[node_name]
        result = node(state)
        if asyncio.iscoroutine(result):
            return await result
        return result

    async def ainvoke(self, state: AgentState | dict[str, Any]) -> AgentState:
        if not isinstance(state, AgentState):
            state = AgentState.model_validate(state)
        state = await self._call(self.start, state)
        route_key = self.selector(state)
        category_node = self.category_nodes.get(route_key)
        if category_node is not None:
            state = await self._call(category_node, state)
        state = await self._call(self.validator_node, state)
        return state


@dataclass(slots=True)
class OrchestrationDependencies:
    """Injected node dependencies for graph construction."""

    routing_agent: RoutingAgent = field(default_factory=RoutingAgent)
    factual_agent: FactualKnowledgeAgent = field(default_factory=FactualKnowledgeAgent)
    math_agent: MathematicalReasoningAgent = field(default_factory=MathematicalReasoningAgent)
    sentiment_agent: SentimentClassificationAgent = field(
        default_factory=SentimentClassificationAgent
    )
    summarization_agent: TextSummarizationAgent = field(
        default_factory=TextSummarizationAgent
    )
    ner_agent: NamedEntityRecognitionAgent = field(default_factory=NamedEntityRecognitionAgent)
    debugging_agent: CodeDebuggingAgent = field(default_factory=CodeDebuggingAgent)
    reasoning_agent: LogicalReasoningAgent = field(default_factory=LogicalReasoningAgent)
    code_generation_agent: CodeGenerationAgent = field(default_factory=CodeGenerationAgent)
    validator: ValidatorNode = field(default_factory=ValidatorNode)


def _category_node_names() -> dict[str, str]:
    return {
        FACTUAL_KNOWLEDGE: "factual_knowledge_agent",
        MATHEMATICAL_REASONING: "math_agent",
        SENTIMENT_CLASSIFICATION: "sentiment_agent",
        TEXT_SUMMARIZATION: "summarization_agent",
        NAMED_ENTITY_RECOGNITION: "ner_agent",
        CODE_DEBUGGING: "debugging_agent",
        LOGICAL_REASONING: "reasoning_agent",
        CODE_GENERATION: "code_generation_agent",
    }


def _category_node_objects(deps: OrchestrationDependencies) -> dict[str, NodeCallable]:
    return {
        "factual_knowledge_agent": deps.factual_agent,
        "math_agent": deps.math_agent,
        "sentiment_agent": deps.sentiment_agent,
        "summarization_agent": deps.summarization_agent,
        "ner_agent": deps.ner_agent,
        "debugging_agent": deps.debugging_agent,
        "reasoning_agent": deps.reasoning_agent,
        "code_generation_agent": deps.code_generation_agent,
    }


def build_orchestration_graph(
    dependencies: OrchestrationDependencies | None = None,
) -> Any:
    """Build the orchestration graph."""
    deps = dependencies or OrchestrationDependencies()
    graph = StateGraph(AgentState)
    graph.add_node("routing_agent", deps.routing_agent)
    graph.add_node("validator", deps.validator)

    category_nodes = _category_node_objects(deps)
    for name, node in category_nodes.items():
        graph.add_node(name, node)

    graph.add_edge(START, "routing_agent")

    def _selector(state: AgentState) -> str:
        return state.category or ""

    graph.add_conditional_edges("routing_agent", _selector, _category_node_names())
    for name in category_nodes:
        graph.add_edge(name, "validator")
    graph.add_edge("validator", END)
    return graph.compile()


def build_graph(dependencies: OrchestrationDependencies | None = None) -> Any:
    """Public graph factory alias."""
    return build_orchestration_graph(dependencies)
