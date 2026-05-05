"""Unit tests for src/agents/signal_agent.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def test_signal_agent_is_strands_agent() -> None:
    mock_model = MagicMock()
    mock_agent_cls = MagicMock()
    mock_agent_cls.return_value = MagicMock()

    with (
        patch("src.agents.signal_agent.AnthropicModel", return_value=mock_model),
        patch("src.agents.signal_agent.Agent", mock_agent_cls),
    ):
        import importlib

        import src.agents.signal_agent as module

        importlib.reload(module)
        mock_agent_cls.assert_called_once()


def test_signal_agent_tools_registered() -> None:
    from src.mcp.bls import get_employment_trend
    from src.mcp.fred import get_delinquency_rate
    from src.mcp.rentcast import get_rent_trend, get_vacancy_rate

    mock_model = MagicMock()
    captured: dict[str, object] = {}

    def capture_agent(**kwargs: object) -> MagicMock:
        captured.update(kwargs)
        return MagicMock()

    with (
        patch("src.agents.signal_agent.AnthropicModel", return_value=mock_model),
        patch("src.agents.signal_agent.Agent", side_effect=capture_agent),
    ):
        import importlib

        import src.agents.signal_agent as module

        importlib.reload(module)

    tools = captured.get("tools", [])
    assert get_delinquency_rate in tools
    assert get_employment_trend in tools
    assert get_rent_trend in tools
    assert get_vacancy_rate in tools


def test_signal_agent_system_prompt() -> None:
    from src.prompts.scoring import SCORING_SYSTEM_PROMPT

    mock_model = MagicMock()
    captured: dict[str, object] = {}

    def capture_agent(**kwargs: object) -> MagicMock:
        captured.update(kwargs)
        return MagicMock()

    with (
        patch("src.agents.signal_agent.AnthropicModel", return_value=mock_model),
        patch("src.agents.signal_agent.Agent", side_effect=capture_agent),
    ):
        import importlib

        import src.agents.signal_agent as module

        importlib.reload(module)

    assert captured.get("system_prompt") == SCORING_SYSTEM_PROMPT
