"""Tests for AnthropicAdapter using an injected mock anthropic client."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from src.llm.adapter import LLMResponse
from src.llm.anthropic import AnthropicAdapter


def _mock_client(
    content_blocks: list[object],
    model: str = "claude-sonnet-4-6",
    stop_reason: str = "end_turn",
    input_tokens: int = 100,
    output_tokens: int = 50,
) -> MagicMock:
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens

    response = MagicMock()
    response.content = content_blocks
    response.model = model
    response.stop_reason = stop_reason
    response.usage = usage

    client = MagicMock()
    client.messages.create.return_value = response
    return client


def _text_block(text: str = "Analysis complete.") -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _tool_block(name: str = "score_signals", tool_input: dict = None) -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.id = "toolu_abc123"
    block.name = name
    block.input = tool_input or {"delinquency_score": 60, "overall_score": 58}
    return block


def test_adapter_requires_api_key_when_no_client() -> None:
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        with pytest.raises(ValueError, match="API key"):
            AnthropicAdapter()


def test_adapter_accepts_injected_client() -> None:
    client = _mock_client([_text_block()])
    adapter = AnthropicAdapter(client=client)
    assert adapter is not None


def test_complete_returns_llm_response() -> None:
    client = _mock_client([_text_block("Hello")])
    adapter = AnthropicAdapter(client=client)

    result = adapter.complete(
        messages=[{"role": "user", "content": "Score ZIP 10001."}],
        system="You are a CRE analyst.",
    )

    assert isinstance(result, LLMResponse)
    assert result.content == "Hello"
    assert result.tool_calls == ()
    assert result.stop_reason == "end_turn"


def test_complete_extracts_tool_call() -> None:
    tool_input = {
        "delinquency_score": 60,
        "employment_score": 55,
        "rent_vacancy_score": 50,
        "overall_score": 57,
        "rationale": "Elevated delinquency.",
    }
    client = _mock_client([_tool_block("score_signals", tool_input)])
    adapter = AnthropicAdapter(client=client)

    result = adapter.complete(
        messages=[{"role": "user", "content": "Score ZIP 10001."}],
        system="You are a CRE analyst.",
        tools=[{"name": "score_signals", "input_schema": {}}],
        tool_choice={"type": "tool", "name": "score_signals"},
    )

    assert len(result.tool_calls) == 1
    tc = result.tool_calls[0]
    assert tc["name"] == "score_signals"
    assert tc["input"] == tool_input
    assert tc["id"] == "toolu_abc123"


def test_complete_passes_system_and_tool_choice_to_client() -> None:
    client = _mock_client([_text_block()])
    adapter = AnthropicAdapter(client=client)
    system = "You are a CRE analyst."
    tool_choice = {"type": "tool", "name": "score_signals"}

    adapter.complete(
        messages=[{"role": "user", "content": "Score."}],
        system=system,
        tool_choice=tool_choice,
    )

    call_kwargs = client.messages.create.call_args.kwargs
    assert call_kwargs["system"] == system
    assert call_kwargs["tool_choice"] == tool_choice


def test_complete_usage_mapped_correctly() -> None:
    client = _mock_client([_text_block()], input_tokens=200, output_tokens=75)
    adapter = AnthropicAdapter(client=client)

    result = adapter.complete(
        messages=[{"role": "user", "content": "Score."}],
        system="Analyst.",
    )

    assert result.usage == {"prompt_tokens": 200, "completion_tokens": 75}


def test_get_adapter_returns_anthropic_adapter() -> None:
    from src.llm import get_adapter

    with patch.dict(os.environ, {"LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "test-key"}):
        adapter = get_adapter()

    assert isinstance(adapter, AnthropicAdapter)
