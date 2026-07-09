---
name: prompt-engineering
description: Use when building or editing prompt templates for the Fireworks agent — compressing prompts, structuring output-format instructions, or adapting a prompt to a new task category. Covers prompt compression, structured prompting, and output formatting for token efficiency.
---

# Prompt Engineering

Goal: maximum accuracy per token. See `rules/prompts.md` and `rules/token-efficiency.md` for the
underlying philosophy — this skill is the applied technique.

## Compression
- Strip filler words, hedges, and repeated instructions
- Replace verbose instructions with terse imperative phrasing
- Collapse multi-sentence context into a single clause where possible

## Structured prompting
- State the task category's expected output shape once, explicitly (e.g. "Return one sentence."
  / "Return JSON: {...}")
- For math/logic categories, allow minimal working only if it measurably improves accuracy —
  verify with `skills/evaluation` before keeping it
- For extraction categories (NER, summarization), give the exact schema the parser expects

## Output formatting
- Never ask for markdown unless the task asks for it
- Match the output format to what the parser expects, so no post-processing is needed

See `examples.md` for before/after compressions and `patterns.md` for reusable templates per
category.
