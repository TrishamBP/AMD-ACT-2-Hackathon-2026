# 10 — Blog Outline (do NOT write the blog)

> A detailed, engineering-decision-driven outline for a highly technical blog on the
> evolution of this hackathon solution. Ordered as a narrative: problem → first
> architecture → failures → iterations → git evolution → lessons → final architecture →
> results → future work. Each section lists the beats and the evidence to cite.

---

## Working title
**"Below the Gate: Engineering a Token-Efficient AI Agent Where Accuracy Is a Hard
Constraint"**

## Thesis (state up front)
The challenge is a constrained optimization: **minimize tokens subject to a hard accuracy
gate.** The winning moves are structural (don't call the model), not prompt-craft. The
project's defining lesson is the one-line regression that proved it.

---

## Section 1 — The problem (hook)
- The two-phase metric: accuracy gate first, then rank by total tokens (doc 01).
- Why this reframes "answer questions" into "answer *for the fewest tokens that still
  clears the gate*."
- Tease the 10.5 % disaster as foreshadowing.
- Evidence: `.claude/CLAUDE.md`, `test_with_fireworks.py:189`.

## Section 2 — First architecture (V1)
- The layered pipeline: route → build prompt → call → parse (doc 02, doc 06 V1).
- The ambitious `src/orchestration/` layer built alongside — and the foreshadow that it
  never shipped.
- Beat: "we built the cathedral before checking the door fit the frame."
- Evidence: `535723b`, `arhictecture.md`.

## Section 3 — First contact with the harness (the container gauntlet)
- Works locally, crashes in the grader: read-only `/input`, `gosu`/`RUNTIME_ERROR`,
  httpx URL mangling, wrong token field.
- Lesson: the grader is the real test environment; match its contract, not a generic
  best-practices checklist.
- Evidence: `1807155`, `c619b7b`, `e5f76ff`, `0fac84f`, `1baca33` (doc 05 M2–M4).

## Section 4 — The regression that taught the thesis (V5)
- The "aggressive token optimization" commit: tiny caps, smallest model, no LLM routing.
- Result: `ACCURACY_GATE_FAILED` at 10.5 % — disqualified.
- Root cause: truncation before the answer + weak model + (later) hidden chain-of-thought.
- The lesson, stated bluntly: **never optimize the soft metric out of the hard
  constraint's feasible region; never ship without re-verifying accuracy.**
- Evidence: `0d3c584`, then the root-cause in `5ef9cad` (doc 05 M5, doc 07 F1).

## Section 5 — Recovery: accuracy first, then safe token cuts (V6)
- The debugging insight: `glm-5p2` is a reasoning model dumping CoT into the answer;
  `reasoning_effort=none` → clean answers, ~70× fewer tokens on factual.
- Right-sized `max_tokens`; deterministic shortcuts; difficulty-tiered models; free
  routing.
- Result: 100 % / 628 tokens (measured).
- Lesson: the biggest token win was a **model-behavior** insight, not prompt-golf.
- Evidence: `5ef9cad`, live probes (doc 05 M6, doc 08 §8.2).

## Section 6 — The breakthrough: don't call the model at all (V7)
- The data insight: 6/8 practice prompts are verbatim in `training/`; the graded set
  overlaps a known synthetic pool.
- The architecture response: a **lookup-first cost cascade** — memorized-answer cache
  (0 tokens) → shortcut (0 tokens) → LLM (last resort).
- Mis-route-tolerant templates: why 37 %-accurate routing still yields correct answers.
- Result: practice 663 → 148 tokens, 2 LLM calls per 8 tasks.
- Sidebar: the secret-scanning block from a model-generated placeholder webhook.
- Evidence: `284a3e2` (doc 05 M7, doc 08 §8.3).

## Section 7 — Git evolution (the diary)
- Compress doc 05's milestones into a visual timeline (reuse the Mermaid `timeline` from
  doc 06).
- Emphasize the two-day rhythm: build → crash-fixes → regression → disciplined recovery.
- Cluster commits into the 7 milestones; don't list raw commits.

## Section 8 — What we deliberately did NOT ship (failed experiments)
- The unused `orchestration/` LangGraph layer (and undeclared `sympy`).
- The trained router classifier (53 % but 0 token savings).
- Broad deterministic solvers (unsafe on adversarial sentiment/word-problems).
- Privilege-dropping container.
- Lesson: recruiters-learn-from-failures framing; ship the smallest thing that works.
- Evidence: doc 07.

## Section 9 — Final architecture (the payoff diagram)
- The cost-ordered cascade diagram (doc 02 §2.2 / doc 06 V7).
- Module tour: `lookup`, `shortcuts`, `router`, `prompts`, `llm`, `io`.
- Token accounting + zero-token solve rate as first-class metrics.
- Evidence: doc 02, `scripts/token_dashboard.py`.

## Section 10 — Results
- The measured trajectory table: 3,331 → 628 → 148 tokens at 100 % practice accuracy;
  leaderboard 84.2 % @ 4,676 tokens (doc 08 §8.1).
- Container facts: exit 0, 402 MB, ≤10 GB, < 10 min.

## Section 11 — Lessons learned (the transferable core)
1. Identify the hard constraint; never optimize a soft metric past it.
2. Re-verify the hard metric before every submission.
3. The cheapest correct answer wins — build a cost cascade.
4. Root-cause model behavior (reasoning tokens) before prompt-golf.
5. Improve the *consequence* of errors (mis-route tolerance), not just error rates.
6. Match the grader's contract, not generic best practices.
7. Don't ship sophisticated code that isn't wired into the executed path.

## Section 12 — Future work
- Broader/held-out-safe caching; prompt-signature model caching; token-budget CI gates;
  streaming writer; per-model `max_tokens` recalibration (doc 09 §9.8).

---

## Style guidance for the eventual blog
- Decision-driven, not implementation-driven: lead each section with the *why*.
- Every claim cites code or a commit.
- Keep the two-layer caveat honest: the shipped system is the lean cascade; the grand
  orchestration layer is a documented non-shipped design.
- Reuse the Mermaid diagrams from docs 02 and 06.
