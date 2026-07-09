"""Convenience wrapper for local execution."""
from __future__ import annotations

import sys

from src.main import main as app_main


if __name__ == "__main__":
    sys.exit(app_main())
