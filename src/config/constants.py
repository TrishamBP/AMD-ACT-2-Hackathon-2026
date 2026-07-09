"""Application constants."""

# Task categories
FACTUAL_KNOWLEDGE = "factual_knowledge"
MATHEMATICAL_REASONING = "mathematical_reasoning"
SENTIMENT_CLASSIFICATION = "sentiment_classification"
TEXT_SUMMARIZATION = "text_summarization"
NAMED_ENTITY_RECOGNITION = "named_entity_recognition"
CODE_DEBUGGING = "code_debugging"
LOGICAL_REASONING = "logical_reasoning"
CODE_GENERATION = "code_generation"

TASK_CATEGORIES = [
    FACTUAL_KNOWLEDGE,
    MATHEMATICAL_REASONING,
    SENTIMENT_CLASSIFICATION,
    TEXT_SUMMARIZATION,
    NAMED_ENTITY_RECOGNITION,
    CODE_DEBUGGING,
    LOGICAL_REASONING,
    CODE_GENERATION,
]

# Default paths
DEFAULT_INPUT_PATH = "/input/tasks.json"
DEFAULT_OUTPUT_PATH = "/output/results.json"
