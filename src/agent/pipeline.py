"""Single task processing pipeline."""
import logging

from src.models.task import Task
from src.models.result import Result
from src.config.settings import Settings
from src.routing.router import route_task
from src.prompts.builder import build_prompt, get_max_tokens
from src.llm.client import call_fireworks
from src.llm.parser import parse_response

logger = logging.getLogger(__name__)


async def process_single_task(task: Task, settings: Settings) -> Result:
    """Process a single task through the pipeline."""
    # Route to determine category and model
    routing_decision = await route_task(task, settings)

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
