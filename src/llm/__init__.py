"""LLM abstraction layer — factory and public exports."""

from __future__ import annotations

import os

from src.llm.adapter import LLMAdapter, LLMResponse
from src.llm.openrouter import OpenRouterAdapter

__all__ = ["LLMAdapter", "LLMResponse", "get_adapter"]


def get_adapter() -> LLMAdapter:
    """Return an LLMAdapter for the configured provider.

    Controlled by the ``LLM_PROVIDER`` env var (default: ``"openrouter"``).

    Raises:
        ValueError: If ``LLM_PROVIDER`` is set to an unrecognised value.
    """
    provider = os.getenv("LLM_PROVIDER", "openrouter")
    if provider == "openrouter":
        return OpenRouterAdapter()
    raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}. Valid values: 'openrouter'")
