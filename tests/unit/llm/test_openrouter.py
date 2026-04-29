"""Tests for OpenRouterAdapter using an injected mock httpx client."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock

import pytest
from src.llm.adapter import LLMResponse
from src.llm.openrouter import OpenRouterAdapter


def _mock_client(body: dict[str, object], status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.text = json.dumps(body)
    resp.json.return_value = body
    client = MagicMock()
    client.post.return_value = resp
    return client


def _text_body(
    content: str = "Analysis complete.", model: str = "anthropic/claude-3-5-sonnet"
) -> dict[str, object]:
    return {
        "id": "chatcmpl-abc",
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
    }


def _tool_body(
    name: str = "score_signals",
    args: dict[str, object] | None = None,
    model: str = "anthropic/claude-3-5-sonnet",
) -> dict[str, object]:
    if args is None:
        args = {"zip_code": "10001", "score": 85}
    return {
        "id": "chatcmpl-def",
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_xyz",
                            "type": "function",
                            "function": {"name": name, "arguments": json.dumps(args)},
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 80, "completion_tokens": 30, "total_tokens": 110},
    }


class TestTextResponse:
    def test_returns_llm_response(self) -> None:
        adapter = OpenRouterAdapter(
            client=_mock_client(_text_body()), api_key="test-key"
        )  # pragma: allowlist secret
        assert isinstance(adapter.complete(messages=[], system="sys"), LLMResponse)

    def test_content_extracted(self) -> None:
        adapter = OpenRouterAdapter(
            client=_mock_client(_text_body(content="Done.")), api_key="test-key"
        )  # pragma: allowlist secret
        assert adapter.complete(messages=[], system="sys").content == "Done."

    def test_tool_calls_empty(self) -> None:
        adapter = OpenRouterAdapter(
            client=_mock_client(_text_body()), api_key="test-key"
        )  # pragma: allowlist secret
        assert adapter.complete(messages=[], system="sys").tool_calls == ()

    def test_stop_reason_stop(self) -> None:
        adapter = OpenRouterAdapter(
            client=_mock_client(_text_body()), api_key="test-key"
        )  # pragma: allowlist secret
        assert adapter.complete(messages=[], system="sys").stop_reason == "stop"

    def test_model_set(self) -> None:
        adapter = OpenRouterAdapter(
            client=_mock_client(_text_body()), api_key="test-key"
        )  # pragma: allowlist secret
        assert adapter.complete(messages=[], system="sys").model == "anthropic/claude-3-5-sonnet"

    def test_usage_tokens(self) -> None:
        result = OpenRouterAdapter(
            client=_mock_client(_text_body()), api_key="test-key"
        ).complete(  # pragma: allowlist secret
            messages=[], system="sys"
        )
        assert result.usage["prompt_tokens"] == 50
        assert result.usage["completion_tokens"] == 20


class TestToolCallResponse:
    def test_tool_calls_not_empty(self) -> None:
        adapter = OpenRouterAdapter(
            client=_mock_client(_tool_body()), api_key="test-key"
        )  # pragma: allowlist secret
        result = adapter.complete(messages=[], system="sys")
        assert len(result.tool_calls) == 1

    def test_tool_call_name(self) -> None:
        adapter = OpenRouterAdapter(
            client=_mock_client(_tool_body(name="score_signals")), api_key="test-key"
        )  # pragma: allowlist secret
        assert adapter.complete(messages=[], system="sys").tool_calls[0]["name"] == "score_signals"

    def test_tool_call_arguments_parsed(self) -> None:
        adapter = OpenRouterAdapter(
            client=_mock_client(_tool_body(args={"zip_code": "10001", "score": 85})),
            api_key="test-key",  # pragma: allowlist secret
        )
        result = adapter.complete(messages=[], system="sys")
        assert result.tool_calls[0]["input"]["zip_code"] == "10001"  # type: ignore[index]

    def test_stop_reason_tool_calls(self) -> None:
        adapter = OpenRouterAdapter(
            client=_mock_client(_tool_body()), api_key="test-key"
        )  # pragma: allowlist secret
        assert adapter.complete(messages=[], system="sys").stop_reason == "tool_calls"

    def test_content_none(self) -> None:
        adapter = OpenRouterAdapter(
            client=_mock_client(_tool_body()), api_key="test-key"
        )  # pragma: allowlist secret
        assert adapter.complete(messages=[], system="sys").content is None


class TestErrors:
    def test_401_raises(self) -> None:
        adapter = OpenRouterAdapter(
            client=_mock_client({"error": "Unauthorized"}, status=401), api_key="test-key"
        )  # pragma: allowlist secret
        with pytest.raises(RuntimeError, match="401"):
            adapter.complete(messages=[], system="sys")

    def test_500_raises(self) -> None:
        adapter = OpenRouterAdapter(
            client=_mock_client({"error": "Server Error"}, status=500), api_key="test-key"
        )  # pragma: allowlist secret
        with pytest.raises(RuntimeError, match="500"):
            adapter.complete(messages=[], system="sys")

    def test_malformed_tool_args_raises(self) -> None:
        body = {
            "id": "chatcmpl-bad",
            "model": "anthropic/claude-3-5-sonnet",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "tc_1",
                                "type": "function",
                                "function": {"name": "score", "arguments": "not-valid-json{"},
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        adapter = OpenRouterAdapter(
            client=_mock_client(body), api_key="test-key"
        )  # pragma: allowlist secret
        with pytest.raises(RuntimeError, match="malformed JSON"):
            adapter.complete(messages=[], system="sys")

    def test_missing_api_key_raises(self) -> None:
        from unittest.mock import patch

        with patch.dict(os.environ, {}, clear=False):
            clean_env = {k: v for k, v in os.environ.items() if k != "OPENROUTER_API_KEY"}
            with patch.dict(os.environ, clean_env, clear=True):
                with pytest.raises(ValueError, match="API key"):
                    OpenRouterAdapter(client=_mock_client(_text_body()))


class TestRequestShape:
    def test_correct_url(self) -> None:
        client = _mock_client(_text_body())
        OpenRouterAdapter(client=client, api_key="test-key").complete(  # pragma: allowlist secret
            messages=[], system="sys"
        )
        assert client.post.call_args[0][0] == "https://openrouter.ai/api/v1/chat/completions"

    def test_authorization_header(self) -> None:
        client = _mock_client(_text_body())
        test_api_key = "test-key"  # pragma: allowlist secret
        OpenRouterAdapter(client=client, api_key=test_api_key).complete(messages=[], system="sys")
        assert (
            client.post.call_args[1]["headers"]["Authorization"] == "Bearer test-key"
        )  # pragma: allowlist secret

    def test_required_headers(self) -> None:
        client = _mock_client(_text_body())
        OpenRouterAdapter(client=client, api_key="k").complete(messages=[], system="sys")
        headers = client.post.call_args[1]["headers"]
        assert "HTTP-Referer" in headers
        assert "X-Title" in headers

    def test_string_system_sent_as_system_message(self) -> None:
        client = _mock_client(_text_body())
        OpenRouterAdapter(client=client, api_key="test-key").complete(  # pragma: allowlist secret
            messages=[], system="You are helpful."
        )
        body = client.post.call_args[1]["json"]
        sys_msgs = [m for m in body["messages"] if m["role"] == "system"]
        assert sys_msgs[0]["content"] == "You are helpful."

    def test_list_system_sent_as_system_message(self) -> None:
        client = _mock_client(_text_body())
        blocks = [{"type": "text", "text": "Static.", "cache_control": {"type": "ephemeral"}}]
        OpenRouterAdapter(client=client, api_key="test-key").complete(  # pragma: allowlist secret
            messages=[], system=blocks
        )
        body = client.post.call_args[1]["json"]
        sys_msgs = [m for m in body["messages"] if m["role"] == "system"]
        assert sys_msgs[0]["content"] == blocks
