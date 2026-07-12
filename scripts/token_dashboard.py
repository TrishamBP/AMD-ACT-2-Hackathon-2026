#!/usr/bin/env python3
"""Token-usage dashboard.

Reads a results file whose entries carry `metadata` (task_id, category, model,
tokens) and prints per-category / per-model / per-route token histograms plus
the zero-token solve rate. Use after a run to spot expensive categories.

Usage:
    python scripts/token_dashboard.py path/to/results_with_metadata.json
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def _load(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "results" in data:
        return list(data["results"])
    if isinstance(data, list):
        return data
    raise SystemExit(f"Unrecognized results format in {path}")


def _bar(value: int, total: int, width: int = 30) -> str:
    if total <= 0:
        return ""
    filled = int(width * value / total)
    return "#" * filled + "." * (width - filled)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 1
    entries = _load(Path(argv[1]))
    if not entries:
        print("No entries found.")
        return 0

    by_category: dict[str, list[int]] = defaultdict(list)
    by_model: dict[str, int] = defaultdict(int)
    total_tokens = 0
    zero_token = 0

    for entry in entries:
        meta = entry.get("metadata", {}) if isinstance(entry, dict) else {}
        category = meta.get("category", "unknown")
        model = meta.get("model", "unknown")
        tokens = int(meta.get("tokens", 0) or 0)
        by_category[category].append(tokens)
        by_model[model] += tokens
        total_tokens += tokens
        if tokens == 0:
            zero_token += 1

    n = len(entries)
    print("=" * 60)
    print(f"TOKEN DASHBOARD  ({n} tasks, {total_tokens:,} total tokens)")
    print("=" * 60)

    print("\nPer-category average tokens:")
    cat_totals = {c: sum(v) for c, v in by_category.items()}
    peak = max(cat_totals.values()) if cat_totals else 0
    for category, toks in sorted(cat_totals.items(), key=lambda kv: -kv[1]):
        count = len(by_category[category])
        avg = toks / count if count else 0
        print(f"  {category:26s} {avg:7.1f} avg  {_bar(toks, peak)}  ({count} tasks)")

    print("\nPer-model total tokens:")
    for model, toks in sorted(by_model.items(), key=lambda kv: -kv[1]):
        label = model if len(model) <= 40 else "..." + model[-37:]
        print(f"  {label:40s} {toks:8,}")

    rate = zero_token / n if n else 0
    print(f"\nZero-token solve rate: {zero_token}/{n} = {rate:.1%}")
    print(f"Avg tokens/task:       {total_tokens / n:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
