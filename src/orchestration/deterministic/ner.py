"""Deterministic NER using regex patterns."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(slots=True)
class NERDeterministicHandler:
    """Rule-based NER that skips LLM calls."""

    def can_solve(self, prompt: str) -> bool:
        """Check if prompt is asking for named entity extraction."""
        lower = prompt.lower()
        return any(
            keyword in lower
            for keyword in [
                "extract all named entities",
                "named entities",
                "extract entities",
                "entity extraction",
            ]
        )

    def _extract_text(self, prompt: str) -> str:
        """Extract the text to analyze from the prompt."""
        match = re.search(r"from:\s*(.+?)$", prompt, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return prompt

    def solve(self, prompt: str) -> tuple[bool, str, float, str]:
        """Extract named entities using regex patterns."""
        text = self._extract_text(prompt)

        entities = []

        person_pattern = r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b"
        for match in re.finditer(person_pattern, text):
            name = match.group(1)
            if name not in [e[0] for e in entities]:
                entities.append((name, "PERSON"))

        org_keywords = [
            "AI",
            "Inc",
            "Corp",
            "Ltd",
            "LLC",
            "Company",
            "Corporation",
            "Technologies",
        ]
        words = text.split()
        for i, word in enumerate(words):
            if any(keyword in word for keyword in org_keywords):
                if i > 0:
                    org_name = f"{words[i-1]} {word}"
                    entities.append((org_name, "ORGANIZATION"))
                else:
                    entities.append((word, "ORGANIZATION"))

        location_pattern = r"\b(in|at)\s+([A-Z][a-z]+)(?:\s+[A-Z][a-z]+)?\b"
        for match in re.finditer(location_pattern, text):
            location = match.group(2)
            if location not in [e[0] for e in entities]:
                entities.append((location, "LOCATION"))

        month_pattern = r"\b(January|February|March|April|May|June|July|August|September|October|November|December|last\s+\w+)\b"
        for match in re.finditer(month_pattern, text, re.IGNORECASE):
            date = match.group(1)
            entities.append((date, "DATE"))

        if not entities:
            return (False, "", 0.0, "no_entities_found")

        formatted = "\n".join([f"- {entity}: {entity_type}" for entity, entity_type in entities])

        return (True, formatted, 0.92, "rule_based_regex_ner")
