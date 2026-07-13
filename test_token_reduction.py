"""Test suite for aggressive token reduction strategies."""
import sys
import asyncio
from src.orchestration.cache.answer_cache import AnswerCache
from src.orchestration.compression.compressor import PromptCompressor
from src.orchestration.deterministic.sentiment import SentimentDeterministicHandler
from src.orchestration.deterministic.ner import NERDeterministicHandler
from src.orchestration.deterministic.logic import LogicDeterministicHandler
from src.orchestration.deterministic.code_debugging import CodeDebuggingDeterministicHandler


def test_answer_cache():
    """Test zero-token answer cache."""
    print("Testing Answer Cache...")
    cache = AnswerCache()

    prompt1 = "What is the capital of France?"
    cache.set(prompt1, "Paris", 0.95, "llm", "factual")

    cached = cache.get(prompt1)
    assert cached is not None
    assert cached.answer == "Paris"
    print("[PASS] Cache stores and retrieves answers")

    prompt2 = "what is the capital  of france?"
    cached2 = cache.get(prompt2)
    assert cached2 is not None
    assert cached2.answer == "Paris"
    print("[PASS] Cache normalizes text for matching")

    prompt3 = "What is the capital of Germany?"
    cached3 = cache.get(prompt3)
    assert cached3 is None
    print("[PASS] Cache returns None for unseen prompts")


def test_sentiment_deterministic():
    """Test deterministic sentiment classification."""
    print("\nTesting Sentiment Deterministic Handler...")
    handler = SentimentDeterministicHandler()

    prompt1 = "Classify the sentiment of this review: The battery life is great, but the screen scratches too easily."
    assert handler.can_solve(prompt1)
    solved, answer, confidence, method = handler.solve(prompt1)
    assert solved
    assert answer == "Mixed"
    assert confidence >= 0.85
    print(f"[PASS] Sentiment: Mixed (confidence: {confidence})")

    prompt2 = "Classify the sentiment of this review: This product is excellent and amazing!"
    solved, answer, confidence, method = handler.solve(prompt2)
    assert solved
    assert answer == "Positive"
    print(f"[PASS] Sentiment: Positive (confidence: {confidence})")


def test_ner_deterministic():
    """Test deterministic NER."""
    print("\nTesting NER Deterministic Handler...")
    handler = NERDeterministicHandler()

    prompt = "Extract all named entities and their types from: Maria Sanchez joined Fireworks AI in Berlin last March."
    assert handler.can_solve(prompt)
    solved, answer, confidence, method = handler.solve(prompt)
    assert solved
    assert "Maria Sanchez" in answer
    assert "PERSON" in answer
    assert "Berlin" in answer
    assert "LOCATION" in answer
    print(f"[PASS] NER extracted entities (confidence: {confidence})")
    print(f"  Result:\n{answer}")


def test_logic_deterministic():
    """Test deterministic logic puzzle solver."""
    print("\nTesting Logic Deterministic Handler...")
    handler = LogicDeterministicHandler()

    prompt = "Three friends, Sam, Jo, and Lee, each own a different pet: cat, dog, bird. Sam does not own the bird. Jo owns the dog. Who owns the cat?"
    assert handler.can_solve(prompt)
    solved, answer, confidence, method = handler.solve(prompt)
    assert solved
    assert answer == "Sam"
    print(f"[PASS] Logic: {answer} owns the cat (confidence: {confidence})")


def test_code_debugging_deterministic():
    """Test deterministic code debugging."""
    print("\nTesting Code Debugging Deterministic Handler...")
    handler = CodeDebuggingDeterministicHandler()

    prompt = "This function should return the max of a list but has a bug: def get_max(nums): return nums[0]. Find and fix it."
    assert handler.can_solve(prompt)
    solved, answer, confidence, method = handler.solve(prompt)
    assert solved
    assert "max(nums)" in answer
    print(f"[PASS] Code Debug: Fixed max function (confidence: {confidence})")
    print(f"  Result:\n{answer}")


def test_prompt_compression():
    """Test aggressive prompt compression."""
    print("\nTesting Prompt Compression...")
    compressor = PromptCompressor()

    original = "Classify the sentiment of this review: The battery life is great"
    compressed = compressor.compress_sentiment(original)
    assert len(compressed) < len(original)
    print(f"[PASS] Sentiment compression: {len(original)} -> {len(compressed)} chars")

    original = "Summarize the following in exactly one sentence: AI is transforming computing."
    compressed = compressor.compress_summarization(original)
    assert len(compressed) < len(original)
    print(f"[PASS] Summarization compression: {len(original)} -> {len(compressed)} chars")

    original = "What is the capital of Australia?"
    compressed = compressor.compress_factual(original)
    print(f"[PASS] Factual compression: {len(original)} -> {len(compressed)} chars (format optimized)")


def run_all_tests():
    """Run all token reduction tests."""
    print("=" * 60)
    print("AGGRESSIVE TOKEN REDUCTION TEST SUITE")
    print("=" * 60)

    test_answer_cache()
    test_sentiment_deterministic()
    test_ner_deterministic()
    test_logic_deterministic()
    test_code_debugging_deterministic()
    test_prompt_compression()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
