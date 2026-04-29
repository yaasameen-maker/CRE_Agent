"""Tests for cache_control block builder helpers."""

from __future__ import annotations

from src.llm.cache import build_cached_system, cached_text


class TestCachedText:
    def test_type_field(self) -> None:
        assert cached_text("hello")["type"] == "text"

    def test_text_field(self) -> None:
        assert cached_text("hello world")["text"] == "hello world"

    def test_cache_control_ephemeral(self) -> None:
        assert cached_text("hello")["cache_control"] == {"type": "ephemeral"}

    def test_empty_string_raises(self) -> None:
        import pytest

        with pytest.raises(ValueError, match="non-empty"):
            cached_text("")


class TestBuildCachedSystem:
    def test_static_only_one_block(self) -> None:
        assert len(build_cached_system("static")) == 1

    def test_static_block_has_cache_control(self) -> None:
        assert build_cached_system("static")[0]["cache_control"] == {"type": "ephemeral"}

    def test_static_block_text(self) -> None:
        assert build_cached_system("static")[0]["text"] == "static"

    def test_with_dynamic_two_blocks(self) -> None:
        assert len(build_cached_system("static", "dynamic")) == 2

    def test_first_block_cached(self) -> None:
        result = build_cached_system("static", "dynamic")
        assert "cache_control" in result[0]

    def test_second_block_not_cached(self) -> None:
        result = build_cached_system("static", "dynamic")
        assert "cache_control" not in result[1]

    def test_second_block_text(self) -> None:
        assert build_cached_system("static", "dynamic")[1]["text"] == "dynamic"

    def test_second_block_type(self) -> None:
        assert build_cached_system("static", "dynamic")[1]["type"] == "text"

    def test_explicit_none_dynamic_one_block(self) -> None:
        assert len(build_cached_system("static", None)) == 1
