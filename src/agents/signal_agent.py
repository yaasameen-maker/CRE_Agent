"""Phase B Strands Agent — scoring oracle with all Phase A MCP tools registered."""

from __future__ import annotations

import os

from strands import Agent
from strands.models.anthropic import AnthropicModel

from src.mcp.bls import get_employment_trend
from src.mcp.fred import get_delinquency_rate
from src.mcp.rentcast import get_rent_trend, get_vacancy_rate
from src.prompts.scoring import SCORING_SYSTEM_PROMPT


def _build_agent() -> Agent:
    model = AnthropicModel(
        model_id=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
    )
    return Agent(
        model=model,
        system_prompt=SCORING_SYSTEM_PROMPT,
        tools=[get_delinquency_rate, get_employment_trend, get_rent_trend, get_vacancy_rate],
    )


signal_agent: Agent = _build_agent()
