"""Input/output validation."""
from src.models.task import Task
from src.models.result import Result


def validate_task(task: Task) -> bool:
    """Validate a task has required fields."""
    return bool(task.task_id and task.prompt)


def validate_result(result: Result) -> bool:
    """Validate a result has required fields."""
    return bool(result.task_id and result.answer is not None)
