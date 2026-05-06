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

        request = self._model.format_request(
            messages=strands_messages,
            tool_specs=tool_specs or None,
            system_prompt=system_str,
            tool_choice=strands_tool_choice,
        )

        # stream() is a synchronous generator in Strands AnthropicModel.
        tool_calls: list[dict[str, object]] = []
        content_text: list[str] = []
        stop_reason = "end_turn"
        usage: dict[str, int] = {}

        current_tool: dict[str, object] | None = None
        current_input_json: list[str] = []

        for chunk in self._model.stream(request):
            if "contentBlockStart" in chunk:
                start = chunk["contentBlockStart"].get("start", {})
                if "toolUse" in start:
                    current_tool = {
                        "id": start["toolUse"].get("toolUseId", ""),
                        "name": start["toolUse"].get("name", ""),
                        "input": {},
                    }
                    current_input_json = []
            elif "contentBlockDelta" in chunk:
                delta = chunk["contentBlockDelta"].get("delta", {})
                if "toolUse" in delta:
                    current_input_json.append(str(delta["toolUse"].get("input", "")))
                elif "text" in delta:
                    content_text.append(str(delta["text"]))
            elif "contentBlockStop" in chunk:
                if current_tool is not None:
                    import json

                    raw_json = "".join(current_input_json)
                    try:
                        current_tool["input"] = json.loads(raw_json) if raw_json else {}
                    except json.JSONDecodeError:
                        current_tool["input"] = {}
                    tool_calls.append(current_tool)
                    current_tool = None
                    current_input_json = []
            elif "messageStop" in chunk:
                stop_reason = chunk["messageStop"].get("stopReason", "end_turn")
            elif "metadata" in chunk:
                u = chunk["metadata"].get("usage", {})
                usage = {
                    "prompt_tokens": int(u.get("inputTokens", 0)),
                    "completion_tokens": int(u.get("outputTokens", 0)),
                }

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
# Module-level Strands model singleton (lazy-initialised).
# ---------------------------------------------------------------------------

_strands_model: Any = None


def _get_strands_model() -> Any:
    """Return the module-level AnthropicModel singleton, creating it if needed."""
    global _strands_model  # noqa: PLW0603
    if _strands_model is None:
        from strands.models.anthropic import AnthropicModel

        _strands_model = AnthropicModel(
            model_id="claude-sonnet-4-5",
            max_tokens=1024,
        )
    return _strands_model


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

    # Step 3: Score via Strands AnthropicModel.
    try:
        model = _get_strands_model()
        adapter = StrandsAdapter(model)
        return score_zip(silver, adapter)  # type: ignore[arg-type]
    except Exception:
        logger.error("ZIP %s: scoring failed", zip_code, exc_info=True)
        return None
