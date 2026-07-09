"""Token tracking decorator for observability."""
import functools
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec, TypeVar

from src.models.response import FireworksResponse

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


class TokenTracker:
    """Tracks token usage across all Fireworks API calls."""

    def __init__(self) -> None:
        """Initialize token tracker."""
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0
        self.call_count = 0
        self.total_latency_ms = 0.0

    def record(self, response: FireworksResponse) -> None:
        """Record token usage from a response."""
        self.total_prompt_tokens += response.token_usage.prompt_tokens
        self.total_completion_tokens += response.token_usage.completion_tokens
        self.total_tokens += response.token_usage.total_tokens
        self.call_count += 1
        self.total_latency_ms += response.latency_ms

    def get_stats(self) -> dict[str, Any]:
        """Get current tracking statistics."""
        return {
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "call_count": self.call_count,
            "total_latency_ms": self.total_latency_ms,
            "avg_latency_ms": (
                self.total_latency_ms / self.call_count if self.call_count > 0 else 0.0
            ),
        }

    def reset(self) -> None:
        """Reset all counters."""
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0
        self.call_count = 0
        self.total_latency_ms = 0.0


# Global tracker instance
_tracker = TokenTracker()


def get_tracker() -> TokenTracker:
    """Get the global token tracker instance."""
    return _tracker


def track_tokens(
    func: Callable[P, Awaitable[R]],
) -> Callable[P, Awaitable[R]]:
    """Decorator to track tokens and latency for Fireworks API calls.

    Usage:
        @track_tokens
        async def my_llm_call(...) -> FireworksResponse:
            ...

    The decorator automatically:
    - Measures execution time
    - Records token usage if result is FireworksResponse
    - Logs call details
    - Integrates with LangSmith (TODO)
    """

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start_time = time.perf_counter()
        task_id = kwargs.get("task_id", "unknown")

        try:
            result = await func(*args, **kwargs)

            duration_ms = (time.perf_counter() - start_time) * 1000

            # If result is FireworksResponse, track tokens
            if isinstance(result, FireworksResponse):
                _tracker.record(result)

                logger.info(
                    "LLM call completed",
                    extra={
                        "task_id": task_id,
                        "model": result.model,
                        "prompt_tokens": result.token_usage.prompt_tokens,
                        "completion_tokens": result.token_usage.completion_tokens,
                        "total_tokens": result.token_usage.total_tokens,
                        "latency_ms": result.latency_ms,
                        "duration_ms": duration_ms,
                    },
                )

            return result

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.error(
                "LLM call failed",
                extra={
                    "task_id": task_id,
                    "error": str(exc),
                    "duration_ms": duration_ms,
                },
            )
            raise

    return wrapper
