"""Writes /output/results.json with orjson for performance."""
import asyncio
from pathlib import Path

import orjson

from src.models.result import Result


async def save_results(results: list[Result], path: Path) -> None:
    """Save results to JSON file using orjson for performance.

    Args:
        path: Path to output results.json file
        results: List of Result objects to write

    Raises:
        OSError: If file cannot be written
    """

    def _save() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

        # Only include task_id and answer (competition format)
        output_data = [
            {"task_id": result.task_id, "answer": result.answer}
            for result in results
        ]

        # orjson is faster and produces smaller output than stdlib json
        # OPT_INDENT_2 for readability (evaluation may inspect output)
        json_bytes = orjson.dumps(
            output_data,
            option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS,
        )

        with path.open("wb") as f:
            f.write(json_bytes)

    await asyncio.to_thread(_save)
