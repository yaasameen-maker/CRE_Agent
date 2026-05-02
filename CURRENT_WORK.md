# Current Work — CRE Signal Agent

**Last updated:** 2026-05-01
**Sprint day:** 4 of 8 (Phase A complete — 10 of 11 Phase A tasks complete)

---

## Phase A: Demo Build (Days 1–4, through 2026-05-01)

Goal: Prove the pipeline works. 3 data sources (FRED, BLS, RentCast), thin LLM adapter + OpenRouter, `python run_demo.py` producing a ranked digest and one opportunity brief.

| Owner | Task | Status | PR | Tests |
|-------|------|--------|----|----|
| Beatrice | DevSecOps pipeline + project docs | ✅ Done | #1 | — |
| Beatrice | LLM abstraction layer (thin adapter + OpenRouter) | ✅ Done | #2 | Passing |
| Beatrice | FRED + BLS + RentCast MCP servers | ✅ Done | #3 | 85 passing |
| Beatrice | Bronze layer (SQLite cache for 3 sources) | ✅ Done | #3 | Included in #3 |
| Beatrice | Silver layer (ZIP normalization, 30-day window) | ✅ Done | — | Passing |
| Beatrice | Gold layer (signal scoring, ranked digest) | ✅ Done | — | Passing |
| Beatrice | Brief generator (1 brief per top signal) | ✅ Done | — | Passing |
| Beatrice | `run_demo.py` script | ✅ Done | — | Passing |
| Yaasameen | Frontend scaffold | ⏳ Day 2–3 | — | — |
| Both | Shared JSON schema (`docs/schema/`) | ⏳ Day 3–4 | — | — |

---

## Architecture Pivot (Saturday 2026-05-02)

Claude API key arrives. Thin adapter replaced with Strands. Prompt caching activates automatically.

| Owner | Task | Status |
|-------|------|--------|
| Beatrice | Add `ANTHROPIC_API_KEY` to `.env`, set `LLM_PROVIDER=anthropic` | Saturday AM |
| Beatrice | Delete `src/llm/adapter.py`, `openrouter.py` | Saturday AM |
| Beatrice | Create `src/agents/signal_agent.py` (Strands Agent) | Saturday AM |
| Beatrice | Smoke test end-to-end with Strands | Saturday PM |

**Phase B begins ONLY AFTER:** Strands pivot smoke test passes + all tests still pass afterward.

---

## Phase B: Full MVP (Days 5–8, 2026-05-02 to 2026-05-06)

Goal: All 7 data sources, full Strands agentic loop, delivery pipeline, frontend integrated.

| Owner | Task | Status |
|-------|------|--------|
| Beatrice | ATTOM, FHFA, Census ACS, HUD MCP servers | Day 5 |
| Beatrice | Full 7-signal scoring via Strands | Day 5–6 |
| Beatrice | Complete brief + action alert logic | Day 6 |
| Beatrice | APScheduler 8am daily trigger | Day 6 |
| Beatrice | SendGrid email + Slack digest | Day 7 |
| Yaasameen | Digest list view | Day 5 |
| Yaasameen | Opportunity card component | Day 5–6 |
| Yaasameen | Brief detail view | Day 6 |
| Yaasameen | Action alert display | Day 7 |
| Both | End-to-end integration test + demo prep | Day 8 |

---

## Blocked / Waiting

| Task | Blocker |
|------|---------|
| Claude API (Strands pivot) | API key arriving Saturday 2026-05-02 |

## Recently Completed

### 2026-05-01 — Phase A backend closeout
- `src/pipeline/normalizer.py`: Silver normalization with freshness gating and null handling
- `src/pipeline/scorer.py`: Gold scoring fixed to consume `LLMResponse.tool_calls`
- `src/pipeline/briefs.py`: Typed opportunity brief generation + Markdown renderer
- `src/pipeline/demo.py`: Demo ZIP resolution and Bronze → Silver → Gold → Brief orchestration
- `run_demo.py`: CLI entrypoint for `python run_demo.py --zips ...`
- `tests/unit/pipeline/` + `tests/integration/test_demo_pipeline.py`: Pipeline, brief, and demo coverage added
- **125 tests** passing across `tests/unit/` and `tests/integration/`

### PR #3 (2026-04-29) — MCP servers + Bronze cache
- `src/mcp/fred.py`: `get_delinquency_rate(series_id)`
- `src/mcp/bls.py`: `get_employment_trend(metro_code)`
- `src/mcp/rentcast.py`: `get_rent_trend(zip_code)`, `get_vacancy_rate(zip_code)`
- `src/mcp/_db.py`: Bronze cache layer (`bronze_get()`, `bronze_set()`, `_get_conn()`)
- `data/migrations/001_bronze_schema.sql`: Bronze schema
- **85 unit tests** passing (all MCP servers + cache tested)

### PR #2 (2026-04-28) — LLM abstraction layer
- `src/llm/adapter.py`: `LLMAdapter` ABC
- `src/llm/openrouter.py`: `OpenRouterAdapter` (active through Friday)
- `src/llm/cache.py`: `cache_control` helpers for prompt caching
- `src/prompts/scoring.py`: System prompt constants + `SCORING_SYSTEM_PROMPT` stub

### PR #1 (2026-04-27) — DevSecOps pipeline + project docs
- CI/CD workflows: `ci.yml`, `security.yml`, `branch-check.yml`
- Pre-commit hooks: ruff, mypy, bandit, detect-secrets
- Project documentation: CLAUDE.md, AGENTS.md, ARCHITECTURE.md, ROADMAP.md, KNOWLEDGE.md, NOTES.md
- Architecture decisions finalized: thin adapter Phase A, Strands pivot Saturday 2026-05-02
