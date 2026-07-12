# Engineering Analysis — Reader's Note & Index

This repository's full engineering postmortem lives in **`engineering_analysis/`**
(10 documents). This file is the entry point and records one clarifying instruction from
the project owner.

## Critical clarification: the pipeline is the pipeline I built — it is NOT RAG

The deliverable template mentions retrieval, embeddings, chunking, and ranking. **This
project does not use RAG.** Those concepts are **reference-only** and appear in the
analysis solely to map the template's vocabulary onto what was actually built.

What was actually built and shipped is a **cost-ordered cascade** in
`src/agent/pipeline.py`:

```
Task
  └─ answer-cache lookup   (src/lookup)      → hit = 0 tokens   [NOT vector retrieval — an exact/normalized dict lookup]
  └─ deterministic shortcut(src/shortcuts)   → hit = 0 tokens   [exact arithmetic/%/unit conversion]
  └─ deterministic routing (src/routing)     → category + model, 0 tokens in the common case
  └─ prompt construction   (src/prompts)     → normalize + budget + compact template
  └─ single LLM call       (src/llm/client)  → reasoning_effort=none, per-category max_tokens
  └─ parse                 (src/llm/parser)  → clean final answer
```

Wherever the analysis says "retrieval," it means the **memorized-answer dictionary
lookup** in `src/lookup/` — an exact-plus-normalized string match against a baked table
of known prompt→answer pairs. There is no vector store, no embeddings, no chunking, no
semantic ranking anywhere in the live system.

There is also a large `src/orchestration/` LangGraph-style layer in the repo. It is
**not imported by the live pipeline** and was never shipped; it is documented as a
non-shipped design in `engineering_analysis/07_failed_experiments.md`.

## Document index

| Doc | Contents |
|---|---|
| [01_project_overview.md](engineering_analysis/01_project_overview.md) | Objective, constraints, two-phase scoring gate, why it's an optimization problem |
| [02_current_architecture.md](engineering_analysis/02_current_architecture.md) | Reverse-engineered live architecture, module-by-module, Mermaid diagrams |
| [03_pipeline_walkthrough.md](engineering_analysis/03_pipeline_walkthrough.md) | One request end-to-end through the cascade, with two traced examples |
| [04_engineering_decisions.md](engineering_analysis/04_engineering_decisions.md) | 12 decisions: why / alternative rejected / trade-offs / impact |
| [05_git_history_analysis.md](engineering_analysis/05_git_history_analysis.md) | The engineering diary — 7 milestones across 12 commits |
| [06_architecture_evolution.md](engineering_analysis/06_architecture_evolution.md) | V1→V7 timeline with per-version diagrams |
| [07_failed_experiments.md](engineering_analysis/07_failed_experiments.md) | 8 failed/abandoned experiments and their lessons |
| [08_token_efficiency_analysis.md](engineering_analysis/08_token_efficiency_analysis.md) | Every token optimization, before/after, estimated savings |
| [09_performance_analysis.md](engineering_analysis/09_performance_analysis.md) | Latency, memory, GPU, tokens, cost, bottlenecks |
| [10_blog_outline.md](engineering_analysis/10_blog_outline.md) | Detailed outline for the eventual engineering blog (blog NOT written) |

## Evidence discipline

Every conclusion in these documents is grounded in **source code, commit history,
configuration, or recorded experiments**. Figures from the offline harness or live probes
are marked **(measured)**; leaderboard facts are marked **(external)**; anything inferred
is marked *(inferred)*. Where multiple explanations are possible, the documents say so.
