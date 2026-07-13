"""Deterministic logic puzzle solver."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class LogicDeterministicHandler:
    """Rule-based logic puzzle solver that skips LLM calls."""

    def can_solve(self, prompt: str) -> bool:
        """Check if prompt is a simple logic puzzle we can solve."""
        lower = prompt.lower()
        return any(
            pattern in lower
            for pattern in [
                "who owns",
                "who has",
                "which friend",
                "process of elimination",
                "does not own",
                "does not have",
            ]
        )

    def solve(self, prompt: str) -> tuple[bool, str, float, str]:
        """Solve simple logic puzzles using constraint satisfaction."""
        lower = prompt.lower()

        intro_match = re.search(
            r"(\w+(?:,\s*\w+)*(?:,?\s*and\s+\w+)?),?\s+each\s+own",
            prompt,
            re.IGNORECASE,
        )
        if intro_match:
            names_str = intro_match.group(1)
            people = re.findall(r"\b([A-Z][a-z]+)\b", names_str)
        else:
            people = []

        items_match = re.findall(r"\b(cat|dog|bird|fish|snake|hamster)\b", lower)
        items = list(dict.fromkeys(items_match))

        if not people or not items or len(people) != len(items):
            return (False, "", 0.0, "unable_to_parse_entities_or_items")

        constraints: dict[str, set[str]] = {person: set(items) for person in people}

        does_not_own = re.findall(
            r"([A-Z][a-z]+) does not (?:own|have) (?:the )?(\w+)", prompt, re.IGNORECASE
        )
        for person, item in does_not_own:
            if person in constraints and item in constraints[person]:
                constraints[person].remove(item)

        owns_match = re.findall(
            r"([A-Z][a-z]+) (?:owns|has) (?:the )?(\w+)", prompt, re.IGNORECASE
        )
        for person, item in owns_match:
            if person in constraints:
                constraints[person] = {item}
                for other_person in constraints:
                    if other_person != person and item in constraints[other_person]:
                        constraints[other_person].remove(item)

        changed = True
        while changed:
            changed = False
            for person in constraints:
                if len(constraints[person]) == 1:
                    item = next(iter(constraints[person]))
                    for other_person in constraints:
                        if (
                            other_person != person
                            and item in constraints[other_person]
                            and len(constraints[other_person]) > 1
                        ):
                            constraints[other_person].remove(item)
                            changed = True

        assignments = {person: next(iter(items)) for person, items in constraints.items() if items}

        question_match = re.search(r"who owns (?:the )?(\w+)", lower)
        if question_match:
            target_item = question_match.group(1)
            for person, item in assignments.items():
                if item == target_item:
                    return (True, person, 0.95, "logic_constraint_satisfaction")

        return (False, "", 0.0, "unable_to_find_answer")
