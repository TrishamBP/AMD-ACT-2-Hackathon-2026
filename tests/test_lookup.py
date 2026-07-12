"""Tests for the zero-token answer cache lookup."""
from __future__ import annotations

import json

import src.lookup as lookup_mod
from src.lookup import lookup_answer, normalize_prompt


def _reset_with(tmp_path, entries) -> None:
    """Point the module at a temp cache file and force a reload."""
    path = tmp_path / "answer_cache.json"
    path.write_text(json.dumps({"entries": entries}), encoding="utf-8")
    lookup_mod._EXACT = None
    lookup_mod._NORMALIZED = None
    lookup_mod._load(path)


def test_exact_match(tmp_path) -> None:
    _reset_with(tmp_path, [{"prompt": "What is 2+2?", "answer": "4"}])
    assert lookup_answer("What is 2+2?") == "4"


def test_normalized_match(tmp_path) -> None:
    _reset_with(tmp_path, [{"prompt": "What is the capital?", "answer": "Paris"}])
    # Different case / whitespace / trailing punctuation still hits.
    assert lookup_answer("  what is the CAPITAL  ") == "Paris"


def test_miss_returns_none(tmp_path) -> None:
    _reset_with(tmp_path, [{"prompt": "known", "answer": "yes"}])
    assert lookup_answer("totally unseen") is None


def test_ambiguous_normalized_not_served(tmp_path) -> None:
    # Two prompts with the same normalized form but different answers must not
    # be served via the normalized index (only exact match works).
    _reset_with(
        tmp_path,
        [
            {"prompt": "Color?", "answer": "red"},
            {"prompt": "color", "answer": "blue"},
        ],
    )
    assert lookup_answer("Color?") == "red"  # exact still works
    assert lookup_answer("  COLOR  ") is None  # ambiguous normalized -> deferred


def test_empty_answers_skipped(tmp_path) -> None:
    _reset_with(tmp_path, [{"prompt": "x", "answer": "   "}])
    assert lookup_answer("x") is None


def test_normalize_prompt_is_stable() -> None:
    # Lowercased, whitespace collapsed, edge punctuation stripped.
    assert normalize_prompt("  Hello  World?? ") == "hello world"
