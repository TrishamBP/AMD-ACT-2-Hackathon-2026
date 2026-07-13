"""Deterministic task handlers that skip LLM calls entirely."""

from .handler import DeterministicHandler
from .sentiment import SentimentDeterministicHandler
from .ner import NERDeterministicHandler
from .logic import LogicDeterministicHandler
from .code_debugging import CodeDebuggingDeterministicHandler

__all__ = [
    "DeterministicHandler",
    "SentimentDeterministicHandler",
    "NERDeterministicHandler",
    "LogicDeterministicHandler",
    "CodeDebuggingDeterministicHandler",
]
