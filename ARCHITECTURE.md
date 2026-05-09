# CRE Signal Agent — Architecture

**Current Status (2026-05-06):** Phase A and Phase B complete and merged to main. 212 passing tests. Phase C (go-live: API keys, smoke test, delivery wiring, scheduler deployment) is in progress.

## Build Phases

**Phase A — Demo (Days 1–4, 2026-05-01) ✅ COMPLETE**
Thin LLM adapter in `src/llm/` calling Claude via OpenRouter. Proved the Medallion pipeline, MCP tool pattern, scoring, brief generation, and `run_demo.py` end-to-end. 125 passing tests.

**Phase B — Full MVP (Days 5–8, 2026-05-06) ✅ COMPLETE**
Strands Agents SDK replaces the thin adapter. `src/llm/openrouter.py` and `src/llm/adapter.py` deleted. `src/agents/` is the LLM entry point. 212 passing tests.

```
src/agents/
  signal_agent.py      # StrandsAdapter bridge; scores one ZIP via Haiku (forced tool use)
  coordinator.py       # asyncio.gather — N parallel signal_agent calls, one per ZIP
  execution_agent.py   # Model/Monitor/Ignore classification + brief generation (Sonnet)
  monitor.py           # APScheduler CronTrigger(hour=8, ET) + --once flag

src/llm/
  adapter.py           # LLMAdapter ABC + LLMResponse — retained as interface contract
  cache.py             # cache_control helpers for prompt caching

src/mcp/
  [7 servers]          # Unchanged — same @tool decorated functions

src/pipeline/
  action.py            # ActionClassification enum (MODEL/MONITOR/IGNORE) + classify_action()
  delivery.py          # SendGrid email digest + Slack post_message (httpx)
  config.py            # NYC_ZIP_CODES frozenset, SCOPE_NYC_ONLY env toggle

src/prompts/
  scoring.py           # System prompt constants — unchanged between phases
```

**Phase C — Go-Live (in progress)**
API keys → smoke test → frontend wiring → delivery verification → scheduler deployment.

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

Each ZIP scoring call uses Haiku (forced tool use, rule-following). Brief generation for MODEL ZIPs uses Sonnet (analytical prose). Both use the same `ANTHROPIC_API_KEY`.

| Task | Model | Rationale |
|------|-------|-----------|
| ZIP distress scoring | `claude-haiku-4-5-20251001` | Structured rubric application; 7 numeric thresholds; forced `score_signals` tool use |
| Opportunity brief generation | `claude-sonnet-4-6` | Nuanced analyst prose; synthesis across all 7 signals; only called for MODEL ZIPs (score ≥ 70) |

```python
# src/agents/signal_agent.py — two lazy singletons, one key
_haiku_model  = AnthropicModel(model_id="claude-haiku-4-5-20251001", max_tokens=1024)  # scoring
_sonnet_model = AnthropicModel(model_id="claude-sonnet-4-6",          max_tokens=2048)  # briefs

def get_sonnet_adapter() -> StrandsAdapter: ...  # used by execution_agent
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

## LLM Layer (Phase B)

`src/llm/` retains the `LLMAdapter` ABC and `LLMResponse` dataclass as the interface contract. `openrouter.py` and the Phase A `anthropic.py` were deleted in Phase B cleanup. Business logic calls `LLMAdapter.complete()` — `StrandsAdapter` in `signal_agent.py` bridges to the Strands `AnthropicModel`.

```
src/llm/
  adapter.py   # LLMAdapter ABC + LLMResponse — interface contract only
  cache.py     # cache_control block helpers (prompt caching)
  # openrouter.py deleted (Phase B cleanup)
```

```python
# src/agents/signal_agent.py — bridge between Strands and LLMAdapter
class StrandsAdapter:
    def complete(self, messages, system, tools=None, tool_choice=None) -> _AdapterResponse:
        # Wraps AnthropicModel.stream(), parses tool-use chunks, logs token cost
        ...
```

## Tech Stack

| Component | Choice | Notes |
|-----------|--------|-------|
| Language | Python 3.11 | |
| LLM — scoring | Anthropic `claude-haiku-4-5-20251001` | `ANTHROPIC_API_KEY` |
| LLM — briefs | Anthropic `claude-sonnet-4-6` | `ANTHROPIC_API_KEY` (same key) |
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
