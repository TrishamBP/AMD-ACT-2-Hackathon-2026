"""Tracing decorators for orchestration nodes."""
from __future__ import annotations

import functools
import inspect
import time
from collections.abc import Callable
from typing import Any, TypeVar

from src.orchestration.factual_knowledge.schemas import ExecutionTrace, TokenUsage
from src.orchestration.logging import log_node_event
from src.orchestration.state.agent_state import AgentState

T = TypeVar("T")


def _token_usage(result: Any) -> TokenUsage:
    usage = getattr(result, "token_usage", None)
    if usage is not None and all(
        hasattr(usage, name) for name in ("prompt_tokens", "completion_tokens", "total_tokens")
    ):
        return TokenUsage(
            prompt_tokens=int(getattr(usage, "prompt_tokens", 0)),
            completion_tokens=int(getattr(usage, "completion_tokens", 0)),
            total_tokens=int(getattr(usage, "total_tokens", 0)),
        )
    return TokenUsage()


def _attach_trace(result: Any, trace: ExecutionTrace) -> Any:
    if isinstance(result, AgentState):
        return result.model_copy(update={"trace": [*result.trace, trace]})
    return result


def trace_node(node_name: str | None = None) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorate a node to capture timing and trace data."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                started_at = time.perf_counter()
                state = args[0] if args else kwargs.get("state")
                task_id = getattr(state, "task_id", None)
                current_node = node_name or func.__name__
                log_node_event("node_start", node=current_node, task_id=task_id)
                result = await func(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - started_at) * 1000.0
                usage = _token_usage(result)
                trace = ExecutionTrace(
                    node_name=current_node,
                    latency_ms=elapsed_ms,
                    selected_model=getattr(result, "selected_model", None),
                    category=getattr(result, "category", None),
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    total_tokens=usage.total_tokens,
                )
                log_node_event(
                    "node_end",
                    node=current_node,
                    task_id=task_id,
                    latency_ms=elapsed_ms,
                    selected_model=trace.selected_model,
                    category=trace.category,
                )
                return _attach_trace(result, trace)

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            started_at = time.perf_counter()
            state = args[0] if args else kwargs.get("state")
            task_id = getattr(state, "task_id", None)
            current_node = node_name or func.__name__
            log_node_event("node_start", node=current_node, task_id=task_id)
            result = func(*args, **kwargs)
            elapsed_ms = (time.perf_counter() - started_at) * 1000.0
            usage = _token_usage(result)
            trace = ExecutionTrace(
                node_name=current_node,
                latency_ms=elapsed_ms,
                selected_model=getattr(result, "selected_model", None),
                category=getattr(result, "category", None),
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
            )
            log_node_event(
                "node_end",
                node=current_node,
                task_id=task_id,
                latency_ms=elapsed_ms,
                selected_model=trace.selected_model,
                category=trace.category,
            )
            return _attach_trace(result, trace)

        return sync_wrapper  # type: ignore[return-value]

    return decorator


def track_tokens(func: Callable[..., T]) -> Callable[..., T]:
    """Decorate a node to preserve token usage metadata."""

    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            result = await func(*args, **kwargs)
            if isinstance(result, AgentState):
                usage = result.token_usage
                if usage.total_tokens == 0:
                    usage = TokenUsage(
                        prompt_tokens=usage.prompt_tokens,
                        completion_tokens=usage.completion_tokens,
                        total_tokens=usage.prompt_tokens + usage.completion_tokens,
                    )
                    return result.model_copy(update={"token_usage": usage})
            return result

        return async_wrapper  # type: ignore[return-value]

    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        result = func(*args, **kwargs)
        if isinstance(result, AgentState):
            usage = result.token_usage
            if usage.total_tokens == 0:
                usage = TokenUsage(
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    total_tokens=usage.prompt_tokens + usage.completion_tokens,
                )
                return result.model_copy(update={"token_usage": usage})
        return result

    return sync_wrapper  # type: ignore[return-value]
