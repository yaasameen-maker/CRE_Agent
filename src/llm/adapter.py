"""LLMAdapter ABC and LLMResponse dataclass."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMResponse:
    """Normalised response returned by every LLMAdapter implementation."""

    content: str | None
    tool_calls: tuple[dict[str, object], ...]
    model: str
    stop_reason: str
    usage: dict[str, int]


class LLMAdapter(ABC):
    """Abstract base class for LLM provider adapters.

    Business logic imports only this ABC. Swapping providers is a single
    env-var change (``LLM_PROVIDER``).
    """

    @abstractmethod
    def complete(
        self,
        messages: list[dict[str, object]],
        system: str | list[dict[str, object]],
        tools: list[dict[str, object]] | None = None,
        tool_choice: dict[str, object] | None = None,
    ) -> LLMResponse:
        """Send a completion request and return a normalised LLMResponse."""
