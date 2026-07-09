# Prompt Compression Examples

Before -> After per category.

**Summarization**
Before: "Please read the following passage carefully and provide a concise summary that captures
the main idea in exactly one sentence, making sure not to add any extra commentary."
After: "Summarize in one sentence:"

**NER**
Before: "I would like you to identify all named entities in the following text, including
people, organizations, locations, and dates, and return them in a well-structured JSON format."
After: `Extract entities (person, org, location, date) as JSON: {"person": [...], "org": [...], "location": [...], "date": [...]}`

**Sentiment**
Before: "Analyze the sentiment of the following text and explain your reasoning in detail before
giving a final classification."
After: "Classify sentiment (positive/negative/neutral) and give one short justification:"

**Code debugging**
Before: "Here is a code snippet that contains a bug. Please carefully review it, explain what is
wrong, and then provide a corrected version of the code."
After: "Find the bug and return corrected code only:"

Rule of thumb: cut anything that doesn't change what the model does.
