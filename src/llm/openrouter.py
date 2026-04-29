"""OpenRouter adapter — OpenAI-compatible chat completions endpoint."""

from __future__ import annotations

import json
import os
from typing import Any, Protocol, runtime_checkable

import httpx

from src.llm.adapter import LLMAdapter, LLMResponse

_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
_HTTP_REFERER = "https://github.com/b-mackenzie-alexander/CRE_Agent"
_X_TITLE = "CRE Signal Agent"
_DEFAULT_MODEL = "anthropic/claude-3-5-sonnet"


@runtime_checkable
class _HttpClient(Protocol):
    """Minimal protocol satisfied by httpx.Client and unittest.mock.MagicMock."""

    def post(
        self,
        url: str,
        *,
        json: dict[str, object],
        headers: dict[str, str],
    ) -> Any: ...

    def close(self) -> None: ...


class OpenRouterAdapter(LLMAdapter):
    """LLMAdapter backed by the OpenRouter API.

    The *client* parameter is injectable so unit tests pass a MagicMock
    without making real HTTP calls.
    """

    def __init__(
        self,
        client: _HttpClient | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self._owns_client: bool = client is None  # True only when we created the client
        self._client: _HttpClient = client or httpx.Client(timeout=60.0)
        self._api_key: str = (
            api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY", "")
        )
        if not self._api_key:
            raise ValueError(
                "OpenRouterAdapter requires an API key. "
                "Pass api_key= or set OPENROUTER_API_KEY in the environment."
            )
        self._model: str = (
            model if model is not None else os.environ.get("OPENROUTER_MODEL", _DEFAULT_MODEL)
        )

    def __del__(self) -> None:
        if self._owns_client:
            self._client.close()

    def complete(
        self,
        messages: list[dict[str, object]],
        system: str | list[dict[str, object]],
        tools: list[dict[str, object]] | None = None,
        tool_choice: dict[str, object] | None = None,
    ) -> LLMResponse:
        """Call the OpenRouter chat completions endpoint.

        Raises:
            RuntimeError: If the HTTP response status code is not 2xx.
        """
        full_messages: list[dict[str, object]] = [
            {"role": "system", "content": system},
            *messages,
        ]
        body: dict[str, object] = {"model": self._model, "messages": full_messages}
        if tools is not None:
            body["tools"] = tools
        if tool_choice is not None:
            body["tool_choice"] = tool_choice

        headers: dict[str, str] = {
            "Authorization": f"Bearer {self._api_key}",
            "HTTP-Referer": _HTTP_REFERER,
            "X-Title": _X_TITLE,
            "Content-Type": "application/json",
        }

        response = self._client.post(_ENDPOINT, json=body, headers=headers)

        if response.status_code < 200 or response.status_code >= 300:
            raise RuntimeError(f"OpenRouter returned HTTP {response.status_code}: {response.text}")

        data: dict[str, Any] = response.json()
        choice = data["choices"][0]
        message = choice["message"]
        finish_reason: str = choice.get("finish_reason") or "stop"
        content: str | None = message.get("content")

        raw_tool_calls: list[dict[str, object]] = []
        for tc in message.get("tool_calls") or []:
            fn = tc.get("function", {})
            raw_args = fn.get("arguments", "{}")
            try:
                parsed: object = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"OpenRouter returned malformed JSON in tool_calls arguments: {exc}"
                ) from exc
            raw_tool_calls.append(
                {"id": tc.get("id", ""), "name": fn.get("name", ""), "input": parsed}
            )

        usage_raw: dict[str, Any] = data.get("usage", {})
        return LLMResponse(
            content=content,
            tool_calls=tuple(raw_tool_calls),
            model=data.get("model", self._model),
            stop_reason=finish_reason,
            usage={
                "prompt_tokens": int(usage_raw.get("prompt_tokens", 0)),
                "completion_tokens": int(usage_raw.get("completion_tokens", 0)),
            },
        )
