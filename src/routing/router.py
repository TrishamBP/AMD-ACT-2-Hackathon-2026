"""Confidence-based hierarchical router."""
from __future__ import annotations

import ast
import json
import math
import re
from dataclasses import dataclass
from typing import Final

from src.config.constants import (
    CODE_DEBUGGING,
    CODE_GENERATION,
    FACTUAL_KNOWLEDGE,
    LOGICAL_REASONING,
    MATHEMATICAL_REASONING,
    NAMED_ENTITY_RECOGNITION,
    SENTIMENT_CLASSIFICATION,
    TASK_CATEGORIES,
    TEXT_SUMMARIZATION,
)
from src.config.settings import Settings
from src.llm.client import call_fireworks
from src.models.task import Task

_CODE_FENCE_RE: Final[re.Pattern[str]] = re.compile(
    r"```(?:[a-zA-Z0-9_+-]+)?\s*(.*?)```",
    re.DOTALL,
)
_JSON_RE: Final[re.Pattern[str]] = re.compile(r"^\s*\{.*\}\s*$", re.DOTALL)


@dataclass(frozen=True)
class ModelMetadata:
    """Metadata parsed from a model identifier."""

    id: str
    family: str
    params_billion: float
    instruction: bool
    reasoning: bool
    vision: bool

    @property
    def sort_key(self) -> tuple[float, str]:
        """Sort smaller compatible models first."""
        return (self.params_billion, self.id)


@dataclass(frozen=True)
class RoutingDecision:
    """Routing result for a task."""

    category: str
    confidence: float
    scores: dict[str, float]
    evidence: dict[str, list[str]]
    model: str
    model_metadata: ModelMetadata
    route_source: str
    runner_up: str | None = None
    margin: float = 0.0


def _normalize_text(prompt: str) -> str:
    return prompt.strip()


def _extract_code_blocks(prompt: str) -> list[str]:
    return [match.group(1).strip() for match in _CODE_FENCE_RE.finditer(prompt)]


def _looks_like_json(prompt: str) -> bool:
    stripped = prompt.strip()
    if _JSON_RE.match(stripped):
        try:
            json.loads(stripped)
        except json.JSONDecodeError:
            return False
        return True
    return False


def _ast_parse_success(prompt: str) -> bool:
    for block in _extract_code_blocks(prompt):
        try:
            ast.parse(block)
        except SyntaxError:
            continue
        return True
    return False


def _score_category(prompt: str) -> tuple[dict[str, float], dict[str, list[str]]]:
    normalized = _normalize_text(prompt)
    lower = normalized.lower()
    length = len(normalized)
    code_blocks = _extract_code_blocks(normalized)
    has_code = bool(code_blocks)
    ast_success = _ast_parse_success(normalized)
    json_detected = _looks_like_json(normalized)
    math_signals = len(re.findall(r"(?<!\w)[\+\-\*/=<>^](?!\w)", normalized)) + len(
        re.findall(r"\b\d+(?:\.\d+)?\b", normalized)
    )

    scores = {category: 0.0 for category in TASK_CATEGORIES}
    evidence: dict[str, list[str]] = {category: [] for category in TASK_CATEGORIES}

    def add(category: str, amount: float, reason: str) -> None:
        if amount <= 0:
            return
        scores[category] = min(1.0, scores[category] + amount)
        evidence[category].append(reason)

    factual_keywords = {
        "who": 0.10,
        "what": 0.10,
        "when": 0.10,
        "where": 0.10,
        "why": 0.10,
        "which": 0.10,
        "identify": 0.15,
        "state": 0.12,
        "explain": 0.08,
        "factual": 0.35,
    }
    math_keywords = {
        "solve": 0.18,
        "calculate": 0.18,
        "compute": 0.18,
        "equation": 0.20,
        "derivative": 0.20,
        "integral": 0.20,
        "probability": 0.15,
        "how many": 0.12,
        "math": 0.15,
    }
    sentiment_keywords = {
        "sentiment": 0.25,
        "positive": 0.20,
        "negative": 0.20,
        "neutral": 0.20,
        "emotion": 0.15,
        "opinion": 0.15,
        "tone": 0.15,
    }
    summary_keywords = {
        "summarize": 0.35,
        "summary": 0.35,
        "tl;dr": 0.30,
        "briefly": 0.15,
        "one sentence": 0.25,
        "concise": 0.20,
        "shorten": 0.20,
    }
    ner_keywords = {
        "extract entities": 0.20,
        "extract the entities": 0.20,
        "named entities": 0.25,
        "entities": 0.18,
        "person": 0.10,
        "organization": 0.10,
        "location": 0.10,
        "date": 0.10,
        "find all": 0.12,
        "list all": 0.12,
    }
    debugging_keywords = {
        "fix": 0.20,
        "debug": 0.20,
        "error": 0.18,
        "bug": 0.18,
        "traceback": 0.20,
        "why does": 0.12,
        "what is wrong": 0.20,
        "correct this": 0.18,
    }
    logic_keywords = {
        "logic": 0.20,
        "deduce": 0.20,
        "infer": 0.15,
        "therefore": 0.12,
        "if": 0.08,
        "then": 0.08,
        "which of": 0.15,
        "true or false": 0.20,
    }
    codegen_keywords = {
        "write code": 0.25,
        "implement": 0.25,
        "function": 0.15,
        "class": 0.15,
        "script": 0.12,
        "python": 0.20,
        "javascript": 0.20,
        "return code": 0.18,
    }

    for phrase, weight in factual_keywords.items():
        if phrase in lower:
            add(FACTUAL_KNOWLEDGE, weight, f"keyword:{phrase}:{weight:.2f}")
    for phrase, weight in math_keywords.items():
        if phrase in lower:
            add(MATHEMATICAL_REASONING, weight, f"keyword:{phrase}:{weight:.2f}")
    for phrase, weight in sentiment_keywords.items():
        if phrase in lower:
            add(SENTIMENT_CLASSIFICATION, weight, f"keyword:{phrase}:{weight:.2f}")
    for phrase, weight in summary_keywords.items():
        if phrase in lower:
            add(TEXT_SUMMARIZATION, weight, f"keyword:{phrase}:{weight:.2f}")
    for phrase, weight in ner_keywords.items():
        if phrase in lower:
            add(NAMED_ENTITY_RECOGNITION, weight, f"keyword:{phrase}:{weight:.2f}")
    for phrase, weight in debugging_keywords.items():
        if phrase in lower:
            add(CODE_DEBUGGING, weight, f"keyword:{phrase}:{weight:.2f}")
    for phrase, weight in logic_keywords.items():
        if phrase in lower:
            add(LOGICAL_REASONING, weight, f"keyword:{phrase}:{weight:.2f}")
    for phrase, weight in codegen_keywords.items():
        if phrase in lower:
            add(CODE_GENERATION, weight, f"keyword:{phrase}:{weight:.2f}")

    if has_code:
        add(CODE_DEBUGGING, 0.35, "signal:code_fence:0.35")
        add(CODE_GENERATION, 0.20, "signal:code_fence:0.20")
    if ast_success:
        add(CODE_DEBUGGING, 0.30, "signal:ast_parse_success:0.30")
        add(CODE_GENERATION, 0.15, "signal:ast_parse_success:0.15")
    if json_detected:
        add(NAMED_ENTITY_RECOGNITION, 0.15, "signal:json_detected:0.15")
    if math_signals:
        math_amount = min(0.20, 0.05 * math_signals)
        add(MATHEMATICAL_REASONING, math_amount, f"signal:math_operators:{math_amount:.2f}")
    if length >= 300:
        add(TEXT_SUMMARIZATION, 0.15, "signal:long_input:0.15")
    if "extract" in lower and "entity" in lower:
        add(NAMED_ENTITY_RECOGNITION, 0.20, "signal:ner_extract:0.20")

    if "?" in normalized and not has_code:
        add(FACTUAL_KNOWLEDGE, 0.10, "signal:question_mark:0.10")

    return scores, evidence


def _select_winner(scores: dict[str, float]) -> tuple[str, float, str | None, float]:
    ordered = sorted(
        scores.items(),
        key=lambda item: (-item[1], item[0]),
    )
    winner, top_score = ordered[0]
    runner_up, runner_score = ordered[1] if len(ordered) > 1 else (None, 0.0)
    margin = max(0.0, top_score - runner_score)
    return winner, top_score, runner_up, margin


def _parse_model_size(model_id: str) -> float:
    match = re.search(r"(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)B", model_id, re.IGNORECASE)
    if match:
        return float(match.group(1)) * float(match.group(2))

    match = re.search(r"(\d+(?:\.\d+)?)B", model_id, re.IGNORECASE)
    if match:
        return float(match.group(1))

    return math.inf


def _infer_model_flags(model_id: str) -> tuple[bool, bool, bool]:
    lowered = model_id.lower()
    instruction = True
    reasoning = any(token in lowered for token in ("reason", "o1", "thinking", "qwen", "deepseek"))
    vision = any(token in lowered for token in ("vision", "vl", "multimodal", "mm"))
    return instruction, reasoning, vision


def _parse_model_metadata(model_id: str) -> ModelMetadata:
    family = model_id.split("/", 1)[-1]
    instruction, reasoning, vision = _infer_model_flags(model_id)
    return ModelMetadata(
        id=model_id,
        family=family,
        params_billion=_parse_model_size(model_id),
        instruction=instruction,
        reasoning=reasoning,
        vision=vision,
    )


def _select_smallest_model(model_ids: list[str]) -> ModelMetadata:
    metadata = [_parse_model_metadata(model_id) for model_id in model_ids]
    compatible = [item for item in metadata if item.instruction]
    chosen_pool = compatible or metadata
    return min(chosen_pool, key=lambda item: item.sort_key)


def _category_min_params(category: str) -> float:
    if category in {SENTIMENT_CLASSIFICATION, NAMED_ENTITY_RECOGNITION}:
        return 1.0
    if category in {FACTUAL_KNOWLEDGE, TEXT_SUMMARIZATION, LOGICAL_REASONING}:
        return 3.0
    if category in {MATHEMATICAL_REASONING, CODE_DEBUGGING, CODE_GENERATION}:
        return 7.0
    return 3.0


def _select_handler_model(category: str, allowed_models: list[str]) -> ModelMetadata:
    metadata = sorted(
        (_parse_model_metadata(model_id) for model_id in allowed_models),
        key=lambda item: item.sort_key,
    )
    compatible = [
        item for item in metadata if item.params_billion >= _category_min_params(category)
    ]
    if compatible:
        return compatible[0]
    return metadata[0]


def _format_router_prompt(prompt: str) -> str:
    return (
        "Classify this task into exactly one category.\n"
        "Respond with ONLY valid JSON in this exact format:\n"
        '{"category":"category_name","confidence":0.95}\n\n'
        "Categories:\n"
        f"- {FACTUAL_KNOWLEDGE}\n"
        f"- {MATHEMATICAL_REASONING}\n"
        f"- {SENTIMENT_CLASSIFICATION}\n"
        f"- {TEXT_SUMMARIZATION}\n"
        f"- {NAMED_ENTITY_RECOGNITION}\n"
        f"- {CODE_DEBUGGING}\n"
        f"- {LOGICAL_REASONING}\n"
        f"- {CODE_GENERATION}\n\n"
        f"Task: {prompt}\n\n"
        "JSON response:"
    )


def _parse_router_json(content: str) -> tuple[str, float]:
    stripped = content.strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("Router response did not contain JSON")

    payload = json.loads(stripped[start : end + 1])
    category = str(payload["category"])
    confidence = float(payload["confidence"])
    if category not in TASK_CATEGORIES:
        raise ValueError(f"Unknown router category: {category}")
    return category, max(0.0, min(1.0, confidence))


async def _fallback_llm_route(prompt: str, settings: Settings) -> tuple[str, float]:
    model = _select_smallest_model(settings.allowed_models)
    response = await call_fireworks(
        _format_router_prompt(prompt),
        model.id,
        settings,
        max_tokens=settings.router_max_tokens,
    )
    return _parse_router_json(response.content)


async def route_task(task: Task, settings: Settings) -> RoutingDecision:
    """Route a task through deterministic rules, then LLM fallback if needed."""
    scores, evidence = _score_category(task.prompt)
    winner, confidence, runner_up, margin = _select_winner(scores)
    should_route_rules = (
        confidence >= settings.router_threshold
        and margin >= settings.router_margin_threshold
    )

    if should_route_rules:
        category = winner
        route_source = "rules"
        route_confidence = confidence
    else:
        try:
            category, route_confidence = await _fallback_llm_route(task.prompt, settings)
            route_source = "llm"
        except Exception:
            category = winner
            route_confidence = confidence
            route_source = "rules_fallback"
        winner, confidence, runner_up, margin = _select_winner(scores)

    model_metadata = _select_handler_model(category, settings.allowed_models)
    return RoutingDecision(
        category=category,
        confidence=route_confidence,
        scores=scores,
        evidence=evidence,
        model=model_metadata.id,
        model_metadata=model_metadata,
        route_source=route_source,
        runner_up=runner_up,
        margin=margin,
    )
