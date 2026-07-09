from __future__ import annotations

import pytest

from src.orchestration.code_generation.agent import CodeGenerationAgent
from src.orchestration.code_generation.prompt_builder import (
    build_code_generation_prompt,
    build_code_repair_prompt,
)
from src.orchestration.code_generation.schemas import CodeGenerationConfig, CodeGenerationInput
from src.orchestration.code_generation.tools import (
    ComplexityDetectorTool,
    LanguageDetectorTool,
    SpecExtractorTool,
)
from src.orchestration.state.agent_state import AgentState


@pytest.mark.asyncio
async def test_language_and_complexity_detectors_identify_python() -> None:
    request = "Write a Python function that merges two sorted arrays in O(n)."
    language = await LanguageDetectorTool().arun(request)
    complexity = await ComplexityDetectorTool().arun(request)

    assert language.language == "python"
    assert language.confidence > 0
    assert complexity.level in {"simple", "medium"}
    assert complexity.score > 0


@pytest.mark.asyncio
async def test_spec_extractor_and_prompt_builder_are_compact() -> None:
    request = "Write a Python function that merges two sorted arrays in O(n)."
    language = await LanguageDetectorTool().arun(request)
    complexity = await ComplexityDetectorTool().arun(request)
    spec = await SpecExtractorTool().arun(request, language, complexity)
    prompt = build_code_generation_prompt(CodeGenerationInput(request=request), spec)

    assert "Return only code." in prompt
    assert "language=python" in prompt
    assert "complexity=" in prompt
    assert "o(n)" in build_code_repair_prompt(
        CodeGenerationInput(request=request),
        spec,
        "def bad(",
        ["syntax_error"],
    )


class _DummyCodeClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls = 0
        self.prompts: list[str] = []

    async def generate(
        self,
        prompt: str,
        *,
        model: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
    ) -> str:
        self.prompts.append(prompt)
        self.calls += 1
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_code_generation_agent_repairs_invalid_python() -> None:
    client = _DummyCodeClient(
        [
            "def add(a, b)\n    return a + b",
            "def add(a, b):\n    return a + b",
        ]
    )
    agent = CodeGenerationAgent(
        client=client,
        config=CodeGenerationConfig(model="demo-model", max_tokens=64, repair_max_tokens=32),
    )
    state = AgentState(
        task_id="task-10",
        original_prompt="Write a Python function that adds two numbers.",
        selected_model="demo-model",
    )

    result = await agent(state)

    assert client.calls == 2
    assert result.category == "code_generation"
    assert result.selected_agent == "CodeGenerationAgent"
    assert result.validated_response is not None
    assert result.validated_response["repaired"] is True
    assert result.validated_response["validation"]["valid"] is True
    assert result.validated_response["formatted_code"] == "def add(a, b):\n    return a + b"
    assert result.trace
