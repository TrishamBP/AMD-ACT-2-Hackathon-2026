"""Orchestrates the entire pipeline."""
import asyncio
import logging
from pathlib import Path

from src.io.reader import load_tasks
from src.io.writer import save_results
from src.agent.executor import execute_tasks
from src.config.settings import load_settings
from src.llm.client import close_fireworks_client

logger = logging.getLogger(__name__)


async def run_pipeline() -> None:
    """Run the complete task processing pipeline."""
    settings = load_settings()
    logger.info(f"Base URL: {settings.base_url}")
    logger.info(f"Allowed models: {settings.allowed_models}")
    try:
        tasks = await load_tasks(Path("/input/tasks.json"))
        logger.info(f"Loaded {len(tasks)} tasks")
        results = await execute_tasks(tasks, settings)
        logger.info(f"Completed {len(results)} results")
        await save_results(results, Path("/output/results.json"))
        logger.info("Results written to /output/results.json")
    finally:
        await close_fireworks_client()
