"""Application entry point."""
import asyncio
import sys
from pathlib import Path

from src.app import run_pipeline
from src.config.logging import setup_logging


def main() -> int:
    """Entry point for the agent."""
    setup_logging()

    try:
        asyncio.run(run_pipeline())
        return 0
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
