"""Tests for the SCORING_SYSTEM_PROMPT constant."""

from __future__ import annotations

from src.llm.cache import build_cached_system
from src.prompts.scoring import SCORING_SYSTEM_PROMPT


class TestScoringSystemPrompt:
    def test_is_string(self) -> None:
        assert isinstance(SCORING_SYSTEM_PROMPT, str)

    def test_is_non_empty(self) -> None:
        assert len(SCORING_SYSTEM_PROMPT.strip()) > 0

    def test_contains_cre_context(self) -> None:
        lower = SCORING_SYSTEM_PROMPT.lower()
        assert any(
            kw in lower for kw in ["commercial real estate", "cre", "distress", "signal", "score"]
        )

    def test_compatible_with_cache_helper(self) -> None:
        blocks = build_cached_system(SCORING_SYSTEM_PROMPT)
        assert blocks[0]["text"] == SCORING_SYSTEM_PROMPT
        assert blocks[0]["cache_control"] == {"type": "ephemeral"}

    def test_compatible_with_dynamic_context(self) -> None:
        blocks = build_cached_system(SCORING_SYSTEM_PROMPT, "Target ZIPs: 10001, 33101")
        assert len(blocks) == 2
        assert "cache_control" not in blocks[1]
