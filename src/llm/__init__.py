"""LLM abstraction layer — Phase A types only.

OpenRouter support was removed in the Phase B pivot.  Use
``src.agents.coordinator.run_coordinator`` for all Phase B scoring.
"""

from __future__ import annotations

from src.llm.adapter import LLMAdapter, LLMResponse

__all__ = ["LLMAdapter", "LLMResponse"]
