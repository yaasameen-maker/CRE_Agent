# CRE Signal Agent — Architecture

**Current Status (2026-05-05):** Phase A is complete and merged to main (PRs #1-5, #8, #9). All 11 backend tasks shipped plus Yaasameen's Action Alerts view (PR #8) and Opportunity Brief detail view (PR #9). Backend verification: 124 passing unit and integration tests. Strands agent layer (`src/agents/`) not yet built — in progress for Phase B.

## Build Phases

This project is built in two architectural phases:

**Phase A — Demo (Days 1–4, through Friday 2026-05-01) ✅ COMPLETE**
Thin custom LLM adapter in `src/llm/`. Single-shot calls to Claude via OpenRouter. Phase A proved the Medallion pipeline, MCP tool pattern, scoring, brief generation, and `run_demo.py` end-to-end. All 11 tasks shipped and merged to main with 125 passing tests.

**Saturday 2026-05-02 — Architecture Pivot (IN PROGRESS)**
Thin adapter is being replaced with the Strands Agents SDK. Claude API key activates. Prompt caching turns on automatically — `cache_control` blocks are built into prompts from day 1 so nothing changes except the provider.

**Phase B — Full MVP (Days 5–8) — Yaasameen V2 Architecture Adopted**
V2 design uses a coordinator/subagent pattern: one `signal_agent` per ZIP runs in parallel, results flow to an `execution_agent` that classifies and dispatches delivery. `src/llm/` is deleted. `src/agents/` is the new LLM entry point.

Target Phase B structure:
```
src/agents/
  signal_agent.py      # Strands Agent, scores one ZIP, forced tool use
  coordinator.py       # asyncio.gather N signal_agent calls in parallel
  execution_agent.py   # Model/Monitor/Ignore classification + delivery dispatch
  monitor.py           # APScheduler CronTrigger(hour=8, ET)

src/llm/
  cache.py             # cache_control helpers — kept from demo phase
  # adapter.py, openrouter.py deleted

src/mcp/
  [7 servers]          # Unchanged — Strands reads the same @tool decorated functions

src/pipeline/
  action.py            # ActionClassifier + ActionLabel enum (MODEL/MONITOR/IGNORE)
  delivery.py          # SendGrid email digest + Slack post_message
  config.py            # NYC_ZIP_CODES frozenset, SCOPE_NYC_ONLY env toggle

src/prompts/
  scoring.py           # System prompt constants — unchanged between phases
```

**Execution Agent classification thresholds:**
- MODEL (score ≥ 70): opportunity brief + email digest + Slack alert
- MONITOR (score 40–69): watchlist entry + Slack notification
- IGNORE (score < 40): log only, no delivery

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

Phase A implementation now includes:
- `src/pipeline/normalizer.py` for Silver extraction from cached Bronze rows
- `src/pipeline/scorer.py` for Gold scoring and digest ranking
- `src/pipeline/briefs.py` for typed opportunity brief generation and rendering
- `src/pipeline/demo.py` plus `run_demo.py` for the demo orchestration path

## Strands Agentic Loop (Phase B — Yaasameen V2 Design)

The Phase B architecture uses a coordinator/subagent pattern. The coordinator spawns one `signal_agent` per ZIP in parallel. Results flow to the `execution_agent` for classification and delivery dispatch.

```
coordinator.py
  └── asyncio.gather([signal_agent(zip) for zip in nyc_zips])
        └── signal_agent.py (Strands Agent, one ZIP)
              Perceive  → Fetch Silver/Gold data for the ZIP
              Think     → Determine which signals breach thresholds
              Act       → Call MCP tools for context (all 7 sources available)
              Observe   → Validate score_signals tool output against schema
              Adjust    → Retry on malformed output
              Return    → ScoredZIP result

  └── execution_agent.py
        Classify  → MODEL (≥70) / MONITOR (40–69) / IGNORE (<40)
        Dispatch  → brief + email + Slack (MODEL)
                  → watchlist + Slack (MONITOR)
                  → log only (IGNORE)
```

Each `signal_agent` is a Strands Agent wired with the full tool set:

```python
from strands import Agent
from src.mcp import fred, rentcast, bls, attom, fhfa, census, hud
from src.prompts.scoring import SCORING_SYSTEM_PROMPT

signal_agent = Agent(
    model="claude-sonnet-4-6",
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

This is enforced structurally: the brief generation prompt includes the target ZIP's Gold record plus its matching Silver source fields. Claude cannot reference a data point that was not passed in.

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
