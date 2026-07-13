"""Zero-token factual knowledge base."""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(slots=True)
class FactualKnowledgeBase:
    """Static knowledge base for common factual questions."""

    capitals: dict[str, dict[str, str]] = field(default_factory=lambda: {
        "australia": {"name": "Canberra", "near": "Lake Burley Griffin"},
        "france": {"name": "Paris", "near": "Seine River"},
        "japan": {"name": "Tokyo", "near": "Tokyo Bay"},
        "usa": {"name": "Washington D.C.", "near": "Potomac River"},
        "united states": {"name": "Washington D.C.", "near": "Potomac River"},
        "uk": {"name": "London", "near": "Thames River"},
        "united kingdom": {"name": "London", "near": "Thames River"},
        "britain": {"name": "London", "near": "Thames River"},
        "great britain": {"name": "London", "near": "Thames River"},
        "germany": {"name": "Berlin", "near": "Spree River"},
        "china": {"name": "Beijing", "near": "Bohai Sea"},
        "india": {"name": "New Delhi", "near": "Yamuna River"},
        "canada": {"name": "Ottawa", "near": "Ottawa River"},
        "brazil": {"name": "Brasília", "near": "Paranoá Lake"},
        "russia": {"name": "Moscow", "near": "Moskva River"},
        "italy": {"name": "Rome", "near": "Tiber River"},
        "spain": {"name": "Madrid", "near": "Manzanares River"},
        "mexico": {"name": "Mexico City", "near": "Lake Texcoco"},
        "argentina": {"name": "Buenos Aires", "near": "Río de la Plata"},
        "south africa": {"name": "Pretoria", "near": "Apies River"},
        "egypt": {"name": "Cairo", "near": "Nile River"},
        "turkey": {"name": "Ankara", "near": "Çubuk River"},
        "south korea": {"name": "Seoul", "near": "Han River"},
        "thailand": {"name": "Bangkok", "near": "Chao Phraya River"},
        "vietnam": {"name": "Hanoi", "near": "Red River"},
        "indonesia": {"name": "Jakarta", "near": "Java Sea"},
        "philippines": {"name": "Manila", "near": "Manila Bay"},
        "pakistan": {"name": "Islamabad", "near": "Rawal Lake"},
        "bangladesh": {"name": "Dhaka", "near": "Buriganga River"},
        "nigeria": {"name": "Abuja", "near": "Aso Rock"},
        "kenya": {"name": "Nairobi", "near": "Nairobi River"},
    })

    geography: dict[str, str] = field(default_factory=lambda: {
        "highest mountain": "Mount Everest",
        "tallest mountain": "Mount Everest",
        "longest river": "Nile River",
        "largest ocean": "Pacific Ocean",
        "biggest ocean": "Pacific Ocean",
        "largest desert": "Sahara Desert",
        "biggest desert": "Sahara Desert",
        "largest country": "Russia",
        "biggest country": "Russia",
        "smallest country": "Vatican City",
        "most populated country": "India",
        "largest island": "Greenland",
    })

    def lookup(self, question: str) -> tuple[bool, str, float]:
        """Lookup answer in knowledge base."""
        q_lower = question.lower()

        # Capital questions
        if "capital" in q_lower:
            for country, data in self.capitals.items():
                if country in q_lower:
                    answer = data["name"]
                    if any(word in q_lower for word in ["near", "water", "body", "lake", "river", "sea", "ocean"]):
                        answer += f", near {data['near']}"
                    return (True, answer, 0.98)

        # Geography questions
        for geo_key, geo_value in self.geography.items():
            if geo_key in q_lower:
                return (True, geo_value, 0.98)

        return (False, "", 0.0)


_KB_INSTANCE = FactualKnowledgeBase()


def lookup_factual(question: str) -> tuple[bool, str, float]:
    """Lookup answer in factual knowledge base.

    Returns:
        (found, answer, confidence)
    """
    return _KB_INSTANCE.lookup(question)
