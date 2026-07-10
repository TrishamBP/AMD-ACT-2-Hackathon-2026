"""Task executor with async orchestration."""
import asyncio
import logging

from src.models.task import Task
from src.models.result import Result
from src.config.settings import Settings
from src.agent.pipeline import process_single_task

logger = logging.getLogger(__name__)


async def execute_tasks(tasks: list[Task], settings: Settings) -> list[Result]:
    """Execute tasks concurrently with semaphore limiting."""
    semaphore = asyncio.Semaphore(settings.max_concurrency)

    async def execute_with_limit(task: Task) -> Result:
        async with semaphore:
            return await process_single_task(task, settings)

    logger.info(f"Processing {len(tasks)} tasks with concurrency {settings.max_concurrency}")

    results = await asyncio.gather(
        *[execute_with_limit(task) for task in tasks],
        return_exceptions=True,
    )

    # Handle exceptions
    processed_results = []
    for task, result in zip(tasks, results):
        if isinstance(result, Exception):
            logger.error(f"Task {task.task_id} failed: {result}")
            processed_results.append(
                Result(
                    task_id=task.task_id,
                    answer=f"I cannot determine the answer to this question.",
                    metadata={"error": str(result)},
                )
            )
        else:
            processed_results.append(result)

    return processed_results
