---
name: routing
description: Use when deciding which of the 8 task categories a prompt belongs to, or which model/prompt template to route it to. This is decision philosophy, not implementation — covers how to classify tasks reliably and cheaply.
---

# Routing

Goal: classify each task into one of 8 categories (factual, math, sentiment, summarization, NER,
debugging, logic, codegen) cheaply and correctly, then hand it to the matching prompt template
and model.

- Prefer cheap heuristics (keywords, prompt structure, presence of code blocks) before falling
  back to a model call for classification — classification itself costs tokens
- If a model call is used for routing, use the smallest/cheapest `ALLOWED_MODELS` entry
- Route deterministically: the same input should always hit the same category
- When a task is ambiguous between two categories, prefer the category with the cheaper/shorter
  prompt template unless accuracy data (see `skills/evaluation`) says otherwise
- Keep routing decisions logged/traceable so the evaluator agent can audit misroutes
