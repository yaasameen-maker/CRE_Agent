"""Tests for src/agents/signal_agent.py — model singleton factories."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import src.agents.signal_agent as _module
from src.agents.signal_agent import (
    StrandsAdapter,
    _get_haiku_model,
    _get_sonnet_model,
    get_sonnet_adapter,
)


class TestGetHaikuModel:
    def test_initialises_with_haiku_model_id(self) -> None:
        """_get_haiku_model creates AnthropicModel with the Haiku 4.5 model id."""
        saved = _module._haiku_model
        _module._haiku_model = None
        try:
            with patch("strands.models.anthropic.AnthropicModel") as mock_cls:
                mock_instance = MagicMock()
                mock_cls.return_value = mock_instance
                result = _get_haiku_model()
                assert result is mock_instance
                mock_cls.assert_called_once_with(
                    model_id="claude-haiku-4-5-20251001",
                    max_tokens=1024,
                )
        finally:
            _module._haiku_model = saved

    def test_returns_same_instance_on_repeat_calls(self) -> None:
        """Lazy singleton — AnthropicModel is constructed only once."""
        saved = _module._haiku_model
        _module._haiku_model = None
        try:
            with patch("strands.models.anthropic.AnthropicModel") as mock_cls:
                mock_cls.return_value = MagicMock()
                first = _get_haiku_model()
                second = _get_haiku_model()
                assert first is second
                assert mock_cls.call_count == 1
        finally:
            _module._haiku_model = saved


class TestGetSonnetModel:
    def test_initialises_with_sonnet_model_id(self) -> None:
        """_get_sonnet_model creates AnthropicModel with the Sonnet 4.6 model id."""
        saved = _module._sonnet_model
        _module._sonnet_model = None
        try:
            with patch("strands.models.anthropic.AnthropicModel") as mock_cls:
                mock_instance = MagicMock()
                mock_cls.return_value = mock_instance
                result = _get_sonnet_model()
                assert result is mock_instance
                mock_cls.assert_called_once_with(
                    model_id="claude-sonnet-4-6",
                    max_tokens=2048,
                )
        finally:
            _module._sonnet_model = saved

    def test_returns_same_instance_on_repeat_calls(self) -> None:
        """Lazy singleton — AnthropicModel is constructed only once."""
        saved = _module._sonnet_model
        _module._sonnet_model = None
        try:
            with patch("strands.models.anthropic.AnthropicModel") as mock_cls:
                mock_cls.return_value = MagicMock()
                first = _get_sonnet_model()
                second = _get_sonnet_model()
                assert first is second
                assert mock_cls.call_count == 1
        finally:
            _module._sonnet_model = saved


class TestGetSonnetAdapter:
    def test_returns_strands_adapter(self) -> None:
        """get_sonnet_adapter returns a StrandsAdapter wrapping the Sonnet model."""
        saved = _module._sonnet_model
        _module._sonnet_model = None
        try:
            with patch("strands.models.anthropic.AnthropicModel") as mock_cls:
                mock_cls.return_value = MagicMock()
                adapter = get_sonnet_adapter()
                assert isinstance(adapter, StrandsAdapter)
        finally:
            _module._sonnet_model = saved
