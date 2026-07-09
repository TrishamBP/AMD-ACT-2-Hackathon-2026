"""Reads /input/tasks.json with orjson for performance."""
import asyncio
from pathlib import Path

import orjson

from src.models.task import Task, TaskBatch


async def load_tasks(path: Path) -> list[Task]:
    """Load tasks from JSON file using orjson for performance.

    Args:
        path: Path to tasks.json file

    Returns:
        List of validated Task objects

    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If JSON is invalid or tasks don't match schema
    """

    def _load() -> list[Task]:
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {path}")

        with path.open("rb") as f:
            raw_data = orjson.loads(f.read())

        # Support both formats: {"tasks": [...]} or [...]
        if isinstance(raw_data, dict):
            batch = TaskBatch.model_validate(raw_data)
            return batch.tasks
        elif isinstance(raw_data, list):
            return [Task.model_validate(task_data) for task_data in raw_data]
        else:
            raise ValueError(f"Invalid tasks file format: expected list or object with 'tasks' key")

    return await asyncio.to_thread(_load)
