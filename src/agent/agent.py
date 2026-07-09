"""Main agent orchestration."""
from dataclasses import dataclass

from src.models.task import Task
from src.models.result import Result
from src.config.settings import Settings


@dataclass
class Agent:
    """Main autonomous agent."""

    settings: Settings

    async def process(self, task: Task) -> Result:
        """Process a single task."""
        from src.agent.pipeline import process_single_task

        return await process_single_task(task, self.settings)
