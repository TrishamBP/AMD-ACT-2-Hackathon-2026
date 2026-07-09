# Reusable Prompt Templates

One minimal template per category, filled at runtime — never rebuilt from scratch per call.

```
FACTUAL: "{question}"
MATH: "{problem}\nReturn only the final numeric answer."
SENTIMENT: "Classify sentiment (positive/negative/neutral) with one-line justification: {text}"
SUMMARY: "Summarize in {constraint}: {text}"
NER: "Extract entities (person, org, location, date) as JSON: {text}"
DEBUG: "Fix the bug, return corrected code only:\n{code}"
LOGIC: "{puzzle}\nReturn the answer satisfying all constraints."
CODEGEN: "Write a function per this spec:\n{spec}"
```

Keep a single dict/module holding these — never inline-construct prompt strings elsewhere.
