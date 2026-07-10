"""Single task processing pipeline."""
from src.models.task import Task
from src.models.result import Result
from src.config.settings import Settings
from src.routing.router import route_task
from src.prompts.builder import build_prompt
from src.llm.client import call_fireworks
from src.llm.parser import parse_response


async def process_single_task(task: Task, settings: Settings) -> Result:
    """Process a single task through the pipeline."""
    # Route to determine category and model
    routing_decision = await route_task(task, settings)

    # Build prompt
    prompt = build_prompt(task, routing_decision)

    # Call Fireworks
    response = await call_fireworks(
        prompt,
        routing_decision.model,
        settings,
        max_tokens=1024,
        temperature=0.0,
    )

    # Parse response
    answer = parse_response(response, routing_decision.category)

    # Return result
    return Result(
        task_id=task.task_id,
        answer=answer,
        metadata={
            "category": routing_decision.category,
            "model": routing_decision.model,
            "route_source": routing_decision.route_source,
            "router_confidence": routing_decision.confidence,
            "router_margin": routing_decision.margin,
            "router_scores": routing_decision.scores,
            "router_evidence": routing_decision.evidence,
            "model_metadata": {
                "id": routing_decision.model_metadata.id,
                "family": routing_decision.model_metadata.family,
                "params_billion": routing_decision.model_metadata.params_billion,
                "instruction": routing_decision.model_metadata.instruction,
                "reasoning": routing_decision.model_metadata.reasoning,
                "vision": routing_decision.model_metadata.vision,
            },
            "tokens": response.token_usage.total_tokens,
        },
    )
