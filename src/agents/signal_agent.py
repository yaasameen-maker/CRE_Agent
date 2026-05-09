"""Phase B signal agent — score one ZIP code using Strands + AnthropicModel.

Pattern 3 (Python as orchestrator):
1. Call MCP tools directly to populate Bronze cache.
2. normalize_zip() reads Bronze → SilverRecord.
3. StrandsAdapter wraps the Strands AnthropicModel to satisfy LLMAdapter.
4. score_zip() uses StrandsAdapter to call the LLM with forced tool use.
5. Return a GoldRecord (rank=0) or None on failure.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from src.mcp.attom import _fetch_foreclosure_filings
from src.mcp.bls import _fetch_employment_trend
from src.mcp.census import _fetch_demographics
from src.mcp.fhfa import _fetch_price_index
from src.mcp.fred import _fetch_delinquency_rate
from src.mcp.hud import _fetch_hud_vacancy
from src.mcp.rentcast import _fetch_markets
from src.pipeline.normalizer import SilverRecord, normalize_zip
from src.pipeline.scorer import GoldRecord, score_zip

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ZipConfig
# ---------------------------------------------------------------------------

# A typed dict describing one ZIP code's data-source coordinates.
# Keys (required):
#   zip_code       – 5-digit ZIP string
#   metro_code     – BLS LAUS series ID for the metro area
#   fred_series_id – FRED series ID for delinquency rate
# Keys (optional, for 7-signal scoring):
#   census_tract   – 11-digit FIPS census tract code
ZipConfig = dict[str, str]

# ---------------------------------------------------------------------------
# Demo ZIP configs used by monitor.py when no config is injected.
# ---------------------------------------------------------------------------

DEMO_ZIP_CONFIGS: list[ZipConfig] = [
    {
        "zip_code": "10001",
        "metro_code": "LAUMT364002000000003",  # NYC metro unemployment
        "fred_series_id": "DRSREACBS",
        "census_tract": "36061010900",  # Manhattan tract near Penn Station
    },
    {
        "zip_code": "10014",
        "metro_code": "LAUMT364002000000003",
        "fred_series_id": "DRSREACBS",
        "census_tract": "36061011300",  # West Village
    },
    {
        "zip_code": "10036",
        "metro_code": "LAUMT364002000000003",
        "fred_series_id": "DRSREACBS",
        "census_tract": "36061010300",  # Midtown West / Theater District
    },
    {
        "zip_code": "10128",
        "metro_code": "LAUMT364002000000003",
        "fred_series_id": "DRSREACBS",
        "census_tract": "36061014100",  # Upper East Side
    },
    {
        "zip_code": "11201",
        "metro_code": "LAUMT364002000000003",
        "fred_series_id": "DRSREACBS",
        "census_tract": "36047000100",  # Brooklyn Heights
    },
]


# ---------------------------------------------------------------------------
# Strands → LLMAdapter bridge
# ---------------------------------------------------------------------------


class StrandsAdapter:
    """Thin bridge from Strands AnthropicModel to the LLMAdapter interface.

    Calls the Anthropic API directly via the Strands model, parses the
    tool-use blocks from the response, and returns a normalised LLMResponse
    compatible with score_zip() and generate_brief().
    """

    def __init__(self, model: Any) -> None:
        self._model = model

    def complete(
        self,
        messages: list[dict[str, object]],
        system: str | list[dict[str, object]],
        tools: list[dict[str, object]] | None = None,
        tool_choice: dict[str, object] | None = None,
    ) -> Any:
        """Send a completion request through the Strands model.

        Returns an object with a .tool_calls tuple mirroring LLMResponse.
        """
        import asyncio
        import json as _json

        from strands.types.tools import ToolSpec

        # Build Strands ToolSpec list from the raw tool dicts.
        tool_specs: list[ToolSpec] = []
        for t in tools or []:
            tool_specs.append(
                {
                    "name": str(t["name"]),
                    "description": str(t.get("description", "")),
                    "inputSchema": {
                        "json": t.get("input_schema", t.get("inputSchema", {})),
                    },
                }
            )

        # Build system prompt string (cache_control blocks are stripped to text).
        if isinstance(system, str):
            system_str: str | None = system
        else:
            parts = []
            for block in system:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(str(block.get("text", "")))
            system_str = "\n".join(parts) if parts else None

        # Strands ToolChoice type mirrors Anthropic's: {"tool": {"name": ...}}
        strands_tool_choice = None
        if tool_choice:
            tc_type = tool_choice.get("type")
            if tc_type == "tool":
                strands_tool_choice = {"tool": {"name": tool_choice["name"]}}
            elif tc_type == "any":
                strands_tool_choice = {"any": {}}
            elif tc_type == "auto":
                strands_tool_choice = {"auto": {}}

        # Build Strands message format.
        strands_messages = []
        for msg in messages:
            content = msg.get("content", "")
            strands_messages.append(
                {
                    "role": msg["role"],
                    "content": ([{"text": content}] if isinstance(content, str) else content),
                }
            )

        # stream() is an async generator — drive it with asyncio.run() which
        # is safe here because score_zip_for_coordinator runs in a thread-pool
        # executor (no running event loop in that thread).
        async def _collect() -> tuple[
            list[dict[str, object]], list[str], str, dict[str, int]
        ]:
            _tool_calls: list[dict[str, object]] = []
            _content_text: list[str] = []
            _stop_reason = "end_turn"
            _usage: dict[str, int] = {}
            _current_tool: dict[str, object] | None = None
            _current_input_json: list[str] = []

            async for chunk in self._model.stream(
                messages=strands_messages,
                tool_specs=tool_specs or None,
                system_prompt=system_str,
                tool_choice=strands_tool_choice,
            ):
                if "contentBlockStart" in chunk:
                    start = chunk["contentBlockStart"].get("start", {})
                    if "toolUse" in start:
                        _current_tool = {
                            "id": start["toolUse"].get("toolUseId", ""),
                            "name": start["toolUse"].get("name", ""),
                            "input": {},
                        }
                        _current_input_json = []
                elif "contentBlockDelta" in chunk:
                    delta = chunk["contentBlockDelta"].get("delta", {})
                    if "toolUse" in delta:
                        _current_input_json.append(str(delta["toolUse"].get("input", "")))
                    elif "text" in delta:
                        _content_text.append(str(delta["text"]))
                elif "contentBlockStop" in chunk:
                    if _current_tool is not None:
                        raw_json = "".join(_current_input_json)
                        try:
                            _current_tool["input"] = _json.loads(raw_json) if raw_json else {}
                        except _json.JSONDecodeError:
                            _current_tool["input"] = {}
                        _tool_calls.append(_current_tool)
                        _current_tool = None
                        _current_input_json = []
                elif "messageStop" in chunk:
                    _stop_reason = chunk["messageStop"].get("stopReason", "end_turn")
                elif "metadata" in chunk:
                    u = chunk["metadata"].get("usage", {})
                    _usage = {
                        "prompt_tokens": int(u.get("inputTokens", 0)),
                        "completion_tokens": int(u.get("outputTokens", 0)),
                    }

            return _tool_calls, _content_text, _stop_reason, _usage

        tool_calls, content_text, stop_reason, usage = asyncio.run(_collect())

        # Log token usage per call so operator can track spend against budget.
        prompt_t = usage.get("prompt_tokens", 0)
        completion_t = usage.get("completion_tokens", 0)
        model_id = self._model.config.get("model_id", "unknown") if hasattr(self._model, "config") else "unknown"
        if "haiku" in model_id:
            cost = (prompt_t * 0.8 + completion_t * 4) / 1_000_000
        else:
            cost = (prompt_t * 3 + completion_t * 15) / 1_000_000
        logger.info(
            "API call [%s]: %d input + %d output tokens (est. cost $%.4f)",
            model_id,
            prompt_t,
            completion_t,
            cost,
        )

        # Return a duck-typed response object compatible with score_zip / generate_brief.
        return _AdapterResponse(
            content="\n".join(content_text) if content_text else None,
            tool_calls=tuple(tool_calls),
            stop_reason=stop_reason,
            usage=usage,
        )


class _AdapterResponse:
    """Duck-typed response object matching LLMResponse's interface."""

    def __init__(
        self,
        content: str | None,
        tool_calls: tuple[dict[str, object], ...],
        stop_reason: str,
        usage: dict[str, int],
    ) -> None:
        self.content = content
        self.tool_calls = tool_calls
        self.stop_reason = stop_reason
        self.usage = usage


# ---------------------------------------------------------------------------
# Model singletons — lazy-initialised, one per task type.
# Haiku 4.5  → ZIP scoring   (structured rule-following, forced tool use)
# Sonnet 4.6 → Brief writing (nuanced analyst prose, synthesis across signals)
# Both use the same ANTHROPIC_API_KEY.
# ---------------------------------------------------------------------------

_haiku_model: Any = None
_sonnet_model: Any = None


def _get_haiku_model() -> Any:
    """Lazy singleton for ZIP scoring — fast, cheap, accurate on rubric tasks."""
    global _haiku_model  # noqa: PLW0603
    if _haiku_model is None:
        from strands.models.anthropic import AnthropicModel

        _haiku_model = AnthropicModel(
            model_id="claude-haiku-4-5-20251001",
            max_tokens=1024,
        )
    return _haiku_model


def _get_sonnet_model() -> Any:
    """Lazy singleton for brief generation — higher quality analytical writing."""
    global _sonnet_model  # noqa: PLW0603
    if _sonnet_model is None:
        from strands.models.anthropic import AnthropicModel

        _sonnet_model = AnthropicModel(
            model_id="claude-sonnet-4-6",
            max_tokens=2048,
        )
    return _sonnet_model


def get_sonnet_adapter() -> StrandsAdapter:
    """Return a StrandsAdapter wrapping the Sonnet model for brief generation."""
    return StrandsAdapter(_get_sonnet_model())


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def score_zip_for_coordinator(zip_config: ZipConfig) -> GoldRecord | None:
    """Score one ZIP code and return a GoldRecord (rank=0), or None on failure.

    Steps:
    1. Call MCP fetch functions to populate Bronze cache.
    2. normalize_zip() to get SilverRecord.
    3. score_zip() via StrandsAdapter for the LLM scoring call.

    Args:
        zip_config: Dict with keys zip_code, metro_code, fred_series_id.

    Returns:
        GoldRecord on success, None if data is unavailable or scoring fails.
    """
    zip_code = zip_config["zip_code"]
    metro_code = zip_config["metro_code"]
    fred_series_id = zip_config["fred_series_id"]

    census_tract = zip_config.get("census_tract")

    # Step 1: Populate Bronze via MCP tool fetch functions.
    try:
        _fetch_delinquency_rate(fred_series_id)
    except Exception:
        logger.warning("ZIP %s: failed to fetch FRED data", zip_code, exc_info=True)

    try:
        _fetch_employment_trend(metro_code)
    except Exception:
        logger.warning("ZIP %s: failed to fetch BLS data", zip_code, exc_info=True)

    try:
        _fetch_markets(zip_code)
    except Exception:
        logger.warning("ZIP %s: failed to fetch RentCast data", zip_code, exc_info=True)

    try:
        _fetch_foreclosure_filings(zip_code)
    except Exception:
        logger.warning("ZIP %s: failed to fetch ATTOM foreclosure data", zip_code, exc_info=True)

    try:
        _fetch_price_index(metro_code)
    except Exception:
        logger.warning("ZIP %s: failed to fetch FHFA price index", zip_code, exc_info=True)

    if census_tract:
        try:
            _fetch_demographics(census_tract)
        except Exception:
            logger.warning("ZIP %s: failed to fetch Census demographics", zip_code, exc_info=True)

    try:
        _fetch_hud_vacancy(metro_code)
    except Exception:
        logger.warning("ZIP %s: failed to fetch HUD vacancy data", zip_code, exc_info=True)

    # Step 2: Normalize Silver.
    silver: SilverRecord | None = normalize_zip(
        zip_code,
        metro_code,
        fred_series_id,
        census_tract=census_tract,
    )
    if silver is None:
        logger.warning("ZIP %s: Silver normalization returned None (missing/stale data)", zip_code)
        return None

    # Persist Silver so gold_upsert FK constraint is satisfied and API JOINs work.
    from src.pipeline._db import silver_upsert
    silver_upsert(
        zip_code=zip_code,
        delinquency_rate=silver.delinquency_rate,
        delinquency_date=silver.delinquency_date,
        unemployment_rate=silver.unemployment_rate,
        unemployment_mom_change=silver.unemployment_mom_change,
        average_rent=silver.average_rent,
        median_rent=silver.median_rent,
        rent_change_pct=silver.rent_change_pct,
        vacancy_rate=silver.vacancy_rate,
        foreclosure_count=silver.foreclosure_count,
        price_index_change=silver.price_index_change,
        median_household_income=silver.median_household_income,
        hud_vacancy_rate=silver.hud_vacancy_rate,
    )

    # Step 3: Score via Haiku (structured rule-following, no prose needed).
    try:
        model = _get_haiku_model()
        adapter = StrandsAdapter(model)
        return score_zip(silver, adapter)  # type: ignore[arg-type]
    except Exception:
        logger.error("ZIP %s: scoring failed", zip_code, exc_info=True)
        return None
