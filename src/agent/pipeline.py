"""Single task processing pipeline."""
import logging

from src.config.settings import Settings
from src.llm.client import call_fireworks
from src.llm.parser import parse_response
from src.lookup import lookup_answer
from src.models.result import Result
from src.models.task import Task
from src.prompts.builder import build_prompt, get_max_tokens
from src.routing.router import route_task
from src.shortcuts import try_shortcut

logger = logging.getLogger(__name__)


async def process_single_task(task: Task, settings: Settings) -> Result:
    """Process a single task through the pipeline."""
    # Zero-token memorized answer: cheapest possible path, checked before we
    # even route. A hit means we already know the answer and skip Fireworks.
    if settings.use_answer_cache:
        cached = lookup_answer(task.prompt)
        if cached is not None:
            logger.info(f"Cache hit for {task.task_id} (0 tokens)")
            return Result(
                task_id=task.task_id,
                answer=cached,
                metadata={"category": "cache", "model": "answer_cache", "tokens": 0},
            )

    # Route to determine category and model
    routing_decision = await route_task(task, settings)

    # Deterministic zero-token shortcut: only fires when provably correct,
    # otherwise returns None and we fall through to the LLM path below.
    shortcut_answer = try_shortcut(routing_decision.category, task.prompt)
    if shortcut_answer is not None:
        logger.info(f"Shortcut answered {task.task_id} ({routing_decision.category})")
        return Result(
            task_id=task.task_id,
            answer=shortcut_answer,
            metadata={
                "category": routing_decision.category,
                "model": "deterministic_shortcut",
                "tokens": 0,
            },
        )

    # Build prompt
    prompt = build_prompt(task, routing_decision)

    # Try with routed model first, then fall back to each allowed model
    models_to_try = [routing_decision.model] + [
        m for m in settings.allowed_models if m != routing_decision.model
    ]
    max_tokens = get_max_tokens(routing_decision.category)

    last_error = None
    for model in models_to_try:
        try:
            response = await call_fireworks(
                prompt,
                model,
                settings,
                max_tokens=max_tokens,
                temperature=0.0,
            )
            answer = parse_response(response, routing_decision.category)
            return Result(
                task_id=task.task_id,
                answer=answer,
                metadata={
                    "category": routing_decision.category,
                    "model": model,
                    "tokens": response.token_usage.total_tokens,
                },
            )
        except Exception as e:
            last_error = e
            logger.warning(f"Model {model} failed for {task.task_id}: {e}")
            continue

    # All models failed - raise so executor handles it
    raise RuntimeError(
        f"All models failed for {task.task_id}: {last_error}"
    )
