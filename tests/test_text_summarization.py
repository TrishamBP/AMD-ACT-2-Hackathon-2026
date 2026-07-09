from __future__ import annotations

import pytest

from src.orchestration.state.agent_state import AgentState
from src.orchestration.text_summarization.agent import TextSummarizationAgent
from src.orchestration.text_summarization.preprocessing import (
    ConstraintExtractor,
    DocumentAnalyzer,
    TextNormalizer,
)
from src.orchestration.text_summarization.prompt_builder import (
    build_summary_prompt,
    build_summary_repair_prompt,
)
from src.orchestration.text_summarization.schemas import (
    SummaryConstraints,
    SummaryRequest,
)
from src.orchestration.text_summarization.validators import SummaryValidator


@pytest.mark.asyncio
async def test_text_normalizer_and_analyzer_extract_basic_profile() -> None:
    text = "First paragraph.\n\n\nSecond paragraph.  "
    normalized, removed = TextNormalizer().normalize(text)
    profile = DocumentAnalyzer().analyze(text)

    assert normalized == "First paragraph.\n\nSecond paragraph."
    assert removed >= 0
    assert profile.word_count >= 4
    assert profile.paragraph_count == 2


@pytest.mark.asyncio
async def test_constraint_extractor_and_prompt_builder_are_compact() -> None:
    request = SummaryRequest(
        text="Summarize in one sentence and preserve the key facts.",
        preferred_format="plain",
    )
    constraints, evidence = ConstraintExtractor().extract(request.text)
    prompt = build_summary_prompt(request, constraints, DocumentAnalyzer().analyze(request.text))
    repair_prompt = build_summary_repair_prompt(
        request,
        constraints,
        "bad summary",
        ["wrong_sentence_count"],
    )

    assert constraints.target_sentences == 1
    assert "one_sentence" in evidence
    assert "Summarize the following text." in prompt
    assert "Return only the summary." in prompt
    assert "wrong_sentence_count" in repair_prompt


def test_summary_validator_handles_bullets_and_json() -> None:
    bullets = SummaryConstraints(output_format="bullets")
    json_constraints = SummaryConstraints(output_format="json")

    bullet_validation = SummaryValidator().validate("- a\n- b", bullets)
    json_validation = SummaryValidator().validate('{"summary":"ok"}', json_constraints)

    assert bullet_validation.valid is True
    assert json_validation.valid is True


class _DummySummaryClient:
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
async def test_text_summarization_agent_repairs_invalid_summary() -> None:
    client = _DummySummaryClient(
        [
            "This is a very long summary. It has too many sentences. It keeps going.",
            "This is concise.",
        ]
    )
    agent = TextSummarizationAgent(client=client)
    state = AgentState(
        task_id="sum-1",
        original_prompt="Summarize the following text in one sentence.",
        selected_model="demo-model",
    )

    result = await agent(state)

    assert client.calls == 2
    assert result.category == "text_summarization"
    assert result.selected_agent == "TextSummarizationAgent"
    assert result.validated_response is not None
    assert result.validated_response["repaired"] is True
    assert result.validated_response["validation"]["valid"] is True
    assert result.validated_response["summary"] == "This is concise."
    assert result.trace


@pytest.mark.asyncio
async def test_text_summarization_agent_handles_missing_client() -> None:
    agent = TextSummarizationAgent()
    state = AgentState(
        task_id="sum-2",
        original_prompt="Summarize the following article in one sentence.",
        selected_model="demo-model",
    )

    result = await agent(state)

    assert "summary_model_client_not_configured" in result.errors
    assert result.category == "text_summarization"
