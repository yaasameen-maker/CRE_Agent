"""Tests for LLMAdapter ABC and LLMResponse dataclass."""

from __future__ import annotations

import pytest
from src.llm.adapter import LLMAdapter, LLMResponse


class TestLLMResponse:
    def test_fields_exist(self) -> None:
        from dataclasses import fields

        field_names = {f.name for f in fields(LLMResponse)}
        assert field_names == {"content", "tool_calls", "model", "stop_reason", "usage"}

    def test_content_can_be_none(self) -> None:
        resp = LLMResponse(
            content=None,
            tool_calls=(),
            model="anthropic/claude-3-5-sonnet",
            stop_reason="tool_calls",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
        )
        assert resp.content is None

    def test_content_can_be_string(self) -> None:
        resp = LLMResponse(
            content="hello",
            tool_calls=(),
            model="anthropic/claude-3-5-sonnet",
            stop_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
        )
        assert resp.content == "hello"

    def test_tool_calls_stored(self) -> None:
        tc = {"id": "tc_1", "name": "score_signals", "input": {"zip": "10001"}}
        resp = LLMResponse(
            content=None,
            tool_calls=(tc,),
            model="anthropic/claude-3-5-sonnet",
            stop_reason="tool_calls",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
        )
        assert resp.tool_calls[0]["name"] == "score_signals"

    def test_usage_stored(self) -> None:
        resp = LLMResponse(
            content="ok",
            tool_calls=(),
            model="anthropic/claude-3-5-sonnet",
            stop_reason="stop",
            usage={"prompt_tokens": 100, "completion_tokens": 50},
        )
        assert resp.usage["prompt_tokens"] == 100
        assert resp.usage["completion_tokens"] == 50

    def test_response_is_immutable(self) -> None:
        import dataclasses

        resp = LLMResponse(
            content="ok",
            tool_calls=(),
            model="m",
            stop_reason="stop",
            usage={"prompt_tokens": 1, "completion_tokens": 1},
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            resp.content = "mutated"  # type: ignore[misc]


class TestLLMAdapterABC:
    def test_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            LLMAdapter()  # type: ignore[abstract]

    def test_incomplete_subclass_cannot_instantiate(self) -> None:
        class Incomplete(LLMAdapter):
            pass

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_concrete_subclass_works(self) -> None:
        class Concrete(LLMAdapter):
            def complete(
                self,
                messages: list[dict[str, object]],
                system: str | list[dict[str, object]],
                tools: list[dict[str, object]] | None = None,
                tool_choice: dict[str, object] | None = None,
            ) -> LLMResponse:
                return LLMResponse(
                    content="ok",
                    tool_calls=(),
                    model="test",
                    stop_reason="stop",
                    usage={"prompt_tokens": 1, "completion_tokens": 1},
                )

        result = Concrete().complete(messages=[], system="test")
        assert result.content == "ok"
