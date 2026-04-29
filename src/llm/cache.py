"""Helpers to build cache_control-annotated system prompt blocks.

OpenRouter silently ignores ``cache_control`` — that is expected.
The Anthropic Claude API activates caching when the key arrives Saturday.
"""

from __future__ import annotations


def cached_text(text: str) -> dict[str, object]:
    """Wrap *text* in a cache_control block marked ephemeral.

    Raises:
        ValueError: If *text* is empty — an empty block cannot be cached
            by the Anthropic API (minimum 1024 tokens required).
    """
    if not text:
        raise ValueError("cached_text: text must be non-empty")
    return {
        "type": "text",
        "text": text,
        "cache_control": {"type": "ephemeral"},
    }


def build_cached_system(
    static: str,
    dynamic: str | None = None,
) -> list[dict[str, object]]:
    """Build system prompt blocks suitable for prompt caching.

    The *static* block (scoring rubric, thresholds, domain context) is
    cache_control-marked. The optional *dynamic* block (per-request ZIP
    list, etc.) is appended without caching.
    """
    blocks: list[dict[str, object]] = [cached_text(static)]
    if dynamic is not None:
        blocks.append({"type": "text", "text": dynamic})
    return blocks
