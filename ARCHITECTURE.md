# CRE Signal Agent — Architecture

## Build Phases

This project is built in two architectural phases:

**Phase A — Demo (Days 1–4, through Friday 2026-05-01)**
Thin custom LLM adapter in `src/llm/`. Single-shot calls to Claude via OpenRouter. Proves the Medallion pipeline, MCP tool pattern, scoring, and brief generation all work correctly before the Claude API key arrives.

**Saturday 2026-05-02 — Architecture Pivot**
Thin adapter is replaced with the Strands Agents SDK. Claude API key activates. Prompt caching turns on automatically — `cache_control` blocks are built into prompts from day 1 so nothing changes except the provider.

**Phase B — Full MVP (Days 5–8, Saturday onwards)**
Strands agentic loop (Perceive → Think → Act → Observe → Adjust) replaces the manual scoring orchestration. `src/llm/adapter.py`, `openrouter.py`, and `anthropic.py` are deleted. `src/agents/signal_agent.py` is added. `src/mcp/` is completely unchanged — Strands consumes the same `@tool` decorated functions.

Target Strands structure:
```
src/agents/
  signal_agent.py    # Strands Agent(model=claude, tools=[all MCP tools], system=SCORING_PROMPT)

src/llm/
  cache.py           # cache_control helpers — kept from demo phase
  # adapter.py, openrouter.py, anthropic.py are deleted

src/mcp/
  [7 servers]        # Unchanged — Strands reads the same @tool decorated functions

src/prompts/
  scoring.py         # System prompt constants — unchanged between phases
```

---

## System Diagram

```
Public APIs       MCP Servers (src/mcp/)   Bronze Layer         Silver Layer         Gold Layer        LLM Layer       Delivery
-----------       ----------------------   ------------         ------------         ----------        ---------       --------
FRED           →  get_delinquency_rate  →  Raw API cache     →  ZIP-normalized    →  Scored+ranked →  Brief gen    →  SendGrid
ATTOM          →  get_foreclosure_fgs   →  SQLite tables     →  30-day window     →  0–100 score   →  Action alert →  Slack
               →  get_deed_transfers    →  One row per       →  Null-handled      →  Top 5–10      →  Tool use
RentCast       →  get_rent_trend        →  API response      →  Deduplicated      →  Explainable   →  Prompt cache
               →  get_vacancy_rate
BLS            →  get_employment_trend
FHFA           →  get_price_index
Census ACS     →  get_demographics
HUD            →  get_hud_vacancy
                          |
                          └── caches to Bronze on every call
                                                                                          |
                                                                                          v
                                                                              Frontend reads Gold layer JSON
                                                                              (Yaasameen's dashboard)
```

## Medallion Layers

| Layer | Contents | Storage | Owner |
|-------|----------|---------|-------|
| Bronze | Raw API responses, cached verbatim, one row per call | SQLite (`bronze_*` tables) | Beatrice |
| Silver | Normalized records, ZIP-aligned, 30-day rolling window, nulls handled | SQLite (`silver_*` tables) | Beatrice |
| Gold | Scored signals (0–100), ranked, with signal flags and explainability fields | SQLite + JSON export | Beatrice |
| Frontend | Renders Gold layer JSON | Browser | Yaasameen |

Bronze is append-only. Silver is rebuilt from Bronze on each run. Gold is rebuilt from Silver on each run.

## Strands Agentic Loop (Phase B Target)

The Phase B architecture replaces the manual scoring pipeline with a Strands-driven agentic loop:

```
Perceive  → Read Gold layer records for target ZIP codes
Think     → Determine which signals breach thresholds
Act       → Call MCP tools for additional context if needed
Observe   → Validate scoring output against schema
Adjust    → Retry or escalate if output is malformed
Deliver   → Return ranked digest + opportunity briefs
```

The Agent is defined once and reused across scoring runs:

```python
from strands import Agent
from src.mcp import fred, rentcast, bls, attom, fhfa, census, hud
from src.prompts.scoring import SCORING_SYSTEM_PROMPT

signal_agent = Agent(
    model="claude-3-5-sonnet-20241022",
    system_prompt=SCORING_SYSTEM_PROMPT,
    tools=[
        fred.get_delinquency_rate,
        rentcast.get_rent_trend,
        rentcast.get_vacancy_rate,
        bls.get_employment_trend,
        attom.get_foreclosure_filings,
        attom.get_deed_transfers,
        fhfa.get_price_index,
        census.get_demographics,
        hud.get_hud_vacancy,
    ],
)
```

## MCP Servers (Tool Layer)

Each public data source is wrapped in an MCP server — a standardized interface that exposes callable tools to Claude without the model needing to know the underlying API details. MCP servers also handle caching: every API response is written to the Bronze layer on fetch so we never repeat a paid or rate-limited call.

```
src/mcp/
  fred.py       # get_delinquency_rate(series_id) → FRED REST API
  attom.py      # get_foreclosure_filings(zip_code, days_back), get_deed_transfers(zip_code, days_back) → ATTOM
  rentcast.py   # get_rent_trend(zip_code), get_vacancy_rate(zip_code) → RentCast API
  bls.py        # get_employment_trend(metro_code) → BLS API
  fhfa.py       # get_price_index(metro_code) → FHFA API
  census.py     # get_demographics(census_tract) → Census ACS API
  hud.py        # get_hud_vacancy(metro_code) → HUD API
```

Registered tools (the contract Claude sees via @tool schema):

| Tool | Parameters | Source |
|------|-----------|--------|
| `get_foreclosure_filings` | `zip_code: str, days_back: int` | ATTOM |
| `get_deed_transfers` | `zip_code: str, days_back: int` | ATTOM |
| `get_rent_trend` | `zip_code: str` | RentCast |
| `get_vacancy_rate` | `zip_code: str` | RentCast |
| `get_employment_trend` | `metro_code: str` | BLS |
| `get_price_index` | `metro_code: str` | FHFA |
| `get_delinquency_rate` | `series_id: str` | FRED |
| `get_demographics` | `census_tract: str` | Census ACS |
| `get_hud_vacancy` | `metro_code: str` | HUD |

## RAG Layer

The Gold layer functions as the retrieval base for brief generation. When Claude generates an opportunity brief, it retrieves verified property records and market data from the Gold layer as grounding context before writing. Every claim in a generated brief is traceable to a specific source row — no hallucinated data points.

This is enforced structurally: the brief generation prompt includes the raw Gold layer records for the target ZIP as retrieved context. Claude cannot reference a data point that was not passed in.

## LLM Abstraction Layer

```
src/llm/
  adapter.py      # LLMAdapter ABC: complete(messages, system, tools) -> LLMResponse
  openrouter.py   # OpenRouterAdapter(LLMAdapter) — active until Friday 2026-05-01
  anthropic.py    # AnthropicAdapter(LLMAdapter)  — activated Saturday 2026-05-02
  cache.py        # cache_control helpers for prompt caching
```

The adapter interface:

```python
class LLMAdapter(ABC):
    def complete(
        self,
        messages: list[dict],
        system: str | list[dict],  # list[dict] for cache_control blocks
        tools: list[dict] | None = None,
        tool_choice: dict | None = None,
    ) -> LLMResponse: ...
```

Business logic imports `LLMAdapter` only. Swapping providers is a single env var change (`LLM_PROVIDER=openrouter` or `LLM_PROVIDER=anthropic`).

## Tech Stack

| Component | Choice | Notes |
|-----------|--------|-------|
| Language | Python 3.11 | |
| LLM (now) | OpenRouter (Claude model) | `OPENROUTER_API_KEY` |
| LLM (Saturday+) | Anthropic Claude API | `ANTHROPIC_API_KEY` |
| Database | SQLite | `data/cre_signal.db` — Postgres migration path is straightforward |
| Scheduler | APScheduler | In-process; triggers 8am digest pipeline |
| Email delivery | SendGrid | `SENDGRID_API_KEY` |
| Slack delivery | Slack API | `SLACK_BOT_TOKEN` |
| MCP servers | mcp (Python SDK) | Standardized tool layer — wraps each data source, caches to Bronze |
| HTTP client | httpx | Raw HTTP inside MCP server implementations |
| Agent orchestration (Phase B) | Strands Agents SDK | Replaces thin adapter Saturday — agentic loop + native MCP integration |
| Linting | ruff | Lint + format |
| Type checking | mypy | Strict mode |
| Security | bandit + detect-secrets + pip-audit | CI enforced |
| Testing | pytest | Unit + integration |
| CI | GitHub Actions | ci.yml, security.yml, branch-check.yml |

## Data Sources

| Source | What It Provides | API Type |
|--------|-----------------|----------|
| FRED | Macro indicators: vacancy rates, interest rates, unemployment by metro | REST (free) |
| ATTOM | Property-level data: foreclosure activity, distressed sales, assessments | REST (paid sandbox) |
| BLS | Employment by metro and sector, monthly change | REST (free) |
| Census ACS | Population, income, housing unit counts by ZIP | REST (free, API key required) |
| FHFA | House price index by ZIP and metro, quarterly | REST (free) |
| RentCast | Rental market data: median rent, vacancy, rent change by ZIP | REST (50 calls/month free tier) |
| HUD | Vacancy surveys: office and residential vacancy trends by metro | REST (free) |

All responses are cached in Bronze layer on first fetch via the MCP server layer. Never make duplicate API calls.

## Key Design Decisions

- **MCP servers as the tool layer:** All data source access goes through MCP servers in `src/mcp/`. Claude never calls external APIs directly — it calls registered tools. Each tool caches its response to Bronze immediately so rate-limited APIs (RentCast: 50 calls/month) are never called twice for the same data.
- **ZIP-code entity resolution:** MVP scores at ZIP level. No geocoding or parcel-level resolution. Keeps data joins simple and all seven sources have ZIP-code coverage.
- **Forced tool_choice for structured outputs:** Claude is called with `tool_choice: {"type": "tool", "name": "<tool>"}` wherever JSON output is required. Eliminates free-text parsing and guarantees schema conformance.
- **Prompt caching from day 1:** Static system prompts (signal thresholds, scoring rubric, domain context) are structured with `cache_control` blocks. OpenRouter ignores these silently; the Claude API activates them on Saturday. No retrofit needed.
- **Rolling 30-day window:** All Silver layer signals are computed as percentage change over the trailing 30 days. Keeps temporal comparisons consistent across sources with different update frequencies.
- **SQLite for demo:** Eliminates infrastructure setup. The ORM layer uses SQLAlchemy so Postgres migration is a connection string change. `data/` is gitignored.
- **APScheduler in-process:** No external job queue or cron dependency for the demo. Triggers the full Bronze → Silver → Gold → Brief → Delivery pipeline at 8am daily.

## Signal Thresholds

| Signal | Threshold | Direction |
|--------|-----------|-----------|
| Vacancy rate | > +5% (30-day change) | Rising = distress |
| Rent | < -3% (30-day change) | Falling = distress |
| Price growth | < +1% (annualized) | Stagnation = distress |
| Employment | > -2% (30-day change) | Drop = distress |
| Foreclosure | Any activity | Binary flag |

## Shared JSON Schema

The contract between backend (Gold layer output) and frontend (dashboard rendering) lives in:

```
docs/schema/
  signal_digest.json      # Array of scored signals — what the digest list view renders
  opportunity_brief.json  # Per-ZIP brief structure — what the brief detail view renders
  action_alert.json       # Model / Monitor / Ignore classification — what the alert display renders
```

Do not change any schema file without agreement from both Beatrice (backend) and Yaasameen (frontend). These files define the integration boundary.
