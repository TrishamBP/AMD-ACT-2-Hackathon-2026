"""Orchestrates the entire pipeline."""
import asyncio
from pathlib import Path

from src.io.reader import load_tasks
from src.io.writer import save_results
from src.agent.executor import execute_tasks
from src.config.settings import load_settings
from src.llm.client import close_fireworks_client


async def run_pipeline() -> None:
    """Run the complete task processing pipeline."""
    settings = load_settings()
    try:
        tasks = await load_tasks(Path("/input/tasks.json"))
        results = await execute_tasks(tasks, settings)
        await save_results(results, Path("/output/results.json"))
    finally:
        await close_fireworks_client()
