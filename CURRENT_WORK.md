# Current Work — CRE Signal Agent

**Last updated:** 2026-05-02
**Sprint day:** 5 of 8, Saturday (Phase A complete and merged, Phase B pivot starting now)

---

## Phase A: Demo Build (Days 1–4, through 2026-05-01) ✅ COMPLETE

Goal: Prove the pipeline works. 3 data sources (FRED, BLS, RentCast), thin LLM adapter + OpenRouter, `python run_demo.py` producing a ranked digest and one opportunity brief.

All tasks complete and merged to main:

| Owner | Task | Status | PR | Tests |
|-------|------|--------|----|----|
| Beatrice | DevSecOps pipeline + project docs | ✅ Merged | #1 | — |
| Beatrice | LLM abstraction layer (thin adapter + OpenRouter) | ✅ Merged | #2 | 125 total |
| Beatrice | FRED + BLS + RentCast MCP servers | ✅ Merged | #3 | 85 in #3 |
| Beatrice | Bronze layer (SQLite cache for 3 sources) | ✅ Merged | #3 | Included |
| Beatrice | Silver layer (ZIP normalization, 30-day window) | ✅ Merged | #4 | Included |
| Beatrice | Gold layer (signal scoring, ranked digest) | ✅ Merged | #4 | Included |
| Beatrice | Brief generator (1 brief per top signal) | ✅ Merged | #4 | Included |
| Beatrice | `run_demo.py` script | ✅ Merged | #4 | Passing |
| Yaasameen | Frontend scaffold | ✅ Merged | #5 | — |
| Both | Shared JSON schema (`docs/schema/`) | ✅ Merged | #5 | — |

**Backend verification: 125 passing tests.** Frontend ready to consume Gold layer JSON. Phase A proves the pipeline works end-to-end.

---

## Architecture Pivot (Saturday 2026-05-02) — IN PROGRESS

Claude API key arrives. Thin adapter replaced with Strands. Prompt caching activates automatically.

| Owner | Task | Status | Target |
|-------|------|--------|--------|
| Beatrice | Add `ANTHROPIC_API_KEY` to `.env`, set `LLM_PROVIDER=anthropic` | ⏳ In Progress | Saturday AM |
| Beatrice | Delete `src/llm/adapter.py`, `openrouter.py` | ⏳ In Progress | Saturday AM |
| Beatrice | Create `src/agents/signal_agent.py` (Strands Agent) | ⏳ In Progress | Saturday AM |
| Beatrice | Smoke test `python run_demo.py` with Strands | ⏳ In Progress | Saturday PM |

**Phase B gates:** Strands pivot smoke test must pass + all tests still passing + demo produces same digest/brief as Phase A.

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

None — Phase A is complete. Strands pivot is in progress (Saturday 2026-05-02).

## Recently Completed

### 2026-05-02 — Phase A complete and merged to main
- All 11 Phase A tasks shipped: DevSecOps, LLM abstraction, 3 MCP servers, Bronze/Silver/Gold layers, brief generation, demo runner, frontend scaffold, schema
- 125 passing tests: 85 in MCP/Bronze PR #3, remainder in pipeline/demo/integration coverage
- Both backend and frontend code on `main` and ready for Saturday pivot
- Demo ZIPs working: `10001`, `33101`, `60601`, `90210` produce ranked digest + opportunity brief

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
