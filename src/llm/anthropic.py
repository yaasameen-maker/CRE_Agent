"""Anthropic adapter — direct Anthropic Messages API."""

from __future__ import annotations

import os
from typing import Any

import anthropic

from src.llm.adapter import LLMAdapter, LLMResponse

_DEFAULT_MODEL = "claude-sonnet-4-6"


class AnthropicAdapter(LLMAdapter):
    """LLMAdapter backed by the Anthropic Messages API.

    The *client* parameter is injectable so unit tests pass a MagicMock
    without making real API calls.
    """

    def __init__(
        self,
        client: anthropic.Anthropic | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        resolved_key = api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY", "")
        if not resolved_key and client is None:
            raise ValueError(
                "AnthropicAdapter requires an API key. "
                "Pass api_key= or set ANTHROPIC_API_KEY in the environment."
            )
        self._client: anthropic.Anthropic = client or anthropic.Anthropic(api_key=resolved_key)
        self._model: str = (
            model if model is not None else os.environ.get("ANTHROPIC_MODEL", _DEFAULT_MODEL)
        )

    def complete(
        self,
        messages: list[dict[str, object]],
        system: str | list[dict[str, object]],
        tools: list[dict[str, object]] | None = None,
        tool_choice: dict[str, object] | None = None,
    ) -> LLMResponse:
        """Call the Anthropic Messages API and return a normalised LLMResponse.

        Raises:
            anthropic.APIError: On API-level errors.
        """
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": 1024,
            "system": system,
            "messages": messages,
        }
        if tools is not None:
            kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice

        response = self._client.messages.create(**kwargs)

        content_text: str | None = None
        tool_calls: list[dict[str, object]] = []

        for block in response.content:
            if block.type == "text":
                content_text = block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    {
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )

        return LLMResponse(
            content=content_text,
            tool_calls=tuple(tool_calls),
            model=response.model,
            stop_reason=response.stop_reason or "stop",
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
            },
        )
