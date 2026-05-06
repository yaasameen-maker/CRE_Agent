# CRE Signal Agent — Roadmap

**Sprint:** 2026-04-28 to 2026-05-06 (8 working days)
**Repo:** https://github.com/b-mackenzie-alexander/CRE_Agent

---

## Phase A: Demo Build — Prove It Works (Days 1–4, through 2026-05-01) ✅ COMPLETE

Goal: End-to-end pipeline running with 3 data sources, scored by Claude via OpenRouter, producing a ranked digest and one opportunity brief. Thin adapter architecture — gets replaced Saturday.

All Phase A tasks shipped and merged to main. Final status:

- [x] DevSecOps pipeline (CI, pre-commit, branch protection) `[Beatrice]` PR #1
- [x] Project documentation (CLAUDE.md, AGENTS.md, ARCHITECTURE.md, ROADMAP.md, etc.) `[Beatrice]` PR #1
- [x] LLM abstraction layer — thin adapter + OpenRouter adapter `[Beatrice]` PR #2
- [x] MCP servers: FRED, BLS, RentCast (3 of 7) `[Beatrice]` PR #3
- [x] Bronze layer: SQLite cache for 3 sources `[Beatrice]` PR #3 (001_bronze_schema.sql, 85 unit tests)
- [x] Silver layer: ZIP normalization, 30-day window, null handling `[Beatrice]` PR #4
- [x] Gold layer: signal scoring (3 signals), ranked digest `[Beatrice]` PR #4
- [x] Brief generator: one opportunity brief per top signal `[Beatrice]` PR #4
- [x] Demo run script: `python run_demo.py --zips <zip1,zip2,zip3>` `[Beatrice]` PR #4
- [x] Frontend scaffold (project setup, routing, layout) `[Yaasameen]` PR #5
- [x] Shared JSON schema definition `[Both]` PR #5

**Metrics:** 125 passing unit and integration tests. `run_demo.py` produces ranked digest + opportunity brief for demo ZIPs.

---

## Phase B: Full MVP (Days 5–8, 2026-05-02 to 2026-05-06) ✅ COMPLETE

### Block 0 — Documentation Reset ✅ COMPLETE
- [x] ROADMAP.md — updated checklist
- [x] CURRENT_WORK.md — Day 7 actual state
- [x] ARCHITECTURE.md — Yaasameen V2 agent architecture
- [x] README.md — current state and quick start
- [x] NOTES.md + KNOWLEDGE.md — session entries

### Block 1 — Strands Agent Layer ✅ COMPLETE
- [x] `src/agents/signal_agent.py` — Strands Agent, one ZIP, forced tool use scoring
- [x] `src/agents/coordinator.py` — asyncio.gather N signal_agent calls in parallel
- [x] `src/agents/execution_agent.py` — Model/Monitor/Ignore classification + delivery dispatch
- [x] `src/agents/monitor.py` — APScheduler 8am CronTrigger(hour=8, ET)
- [x] Add ANTHROPIC_API_KEY to .env, set LLM_PROVIDER=anthropic
- [x] Smoke test run_demo.py end-to-end with Anthropic key
- [x] All 124 existing tests pass after pivot

### Block 2 — Pipeline Extensions ✅ COMPLETE
- [x] `src/pipeline/action.py` — ActionClassifier + ActionLabel enum (MODEL/MONITOR/IGNORE)
- [x] `src/pipeline/delivery.py` — SendGrid email digest + Slack post_message

### Block 3 — 4 New MCP Servers ✅ COMPLETE
- [x] `src/mcp/attom.py` — get_foreclosure_filings, get_deed_transfers
- [x] `src/mcp/fhfa.py` — get_price_index
- [x] `src/mcp/census.py` — get_demographics
- [x] `src/mcp/hud.py` — get_hud_vacancy
- [x] Unit tests for all 4

### Block 4 — 7-Signal Expansion ✅ COMPLETE
- [x] `data/migrations/003_silver_gold_7signal.sql`
- [x] Expand SilverRecord (4 new nullable fields) in normalizer.py
- [x] Update scoring prompt for 7 signals in prompts/scoring.py
- [x] Add new MCP tools to coordinator.py
- [x] Update affected tests

### Block 5 — NYC Scope ✅ COMPLETE
- [x] `src/pipeline/config.py` — NYC_ZIP_CODES frozenset, SCOPE_NYC_ONLY env toggle
- [x] Scope filter in coordinator.py
- [x] NYC demo ZIPs in demo.py

### Block 6 — Cleanup PR ✅ COMPLETE
- [x] Delete `src/llm/openrouter.py`
- [x] Remove OpenRouter adapter from src/llm/
- [x] Remove openrouter from requirements.txt

### Block 7 — Integration & Demo ✅ COMPLETE
- [x] `tests/integration/test_full_pipeline.py` — full 7-source pipeline test
- [x] All 212 tests green

---

## Phase C: Go-Live Handoff — Yaasameen `[Yaasameen]`

Backend is complete and merged. These tasks unblock live operation and frontend integration.

### Environment Setup (prerequisite for everything below)
- [ ] Add `ANTHROPIC_API_KEY` to `.env` (key already issued)
- [ ] Add `ATTOM_API_KEY`, `FHFA_API_KEY`, `CENSUS_API_KEY`, `HUD_API_KEY` to `.env`
- [ ] Add `SENDGRID_API_KEY` and `SLACK_BOT_TOKEN` to `.env`
- [ ] Set `LLM_PROVIDER=anthropic` in `.env`
- [ ] Set `SCOPE_NYC_ONLY=true` in `.env` (already the default)

### Smoke Test
- [ ] Run `pytest tests/unit/ tests/integration/` — must stay green
- [ ] Run coordinator against 2–3 NYC ZIPs to confirm live scoring produces GoldRecords

### Frontend Integration
- [ ] Wire API responses to the ranked digest view (uses `gold_get_digest()` output schema)
- [ ] Wire opportunity brief to the brief display component
- [ ] Wire Action Alerts (MODEL / MONITOR / IGNORE labels from `ExecutionAgent`)
- [ ] Confirm JSON schema in `src/pipeline/scorer.py::GoldRecord` matches frontend contract

### Delivery Wiring
- [ ] Confirm SendGrid sender domain is verified
- [ ] Confirm Slack bot is installed in the target channel with `chat:write` scope
- [ ] Send one test email via `send_email_digest()` and confirm receipt
- [ ] Post one test Slack message via `post_slack_message()` and confirm delivery

### Scheduler Activation
- [ ] Review `src/agents/monitor.py` — 8am ET CronTrigger, calls `run_coordinator()` then `ExecutionAgent().run()`
- [ ] Decide deployment target (local cron, Railway, Render, etc.) and deploy `monitor.py`
- [ ] Confirm first scheduled run fires and produces Gold records

---

## Post-MVP (Out of Sprint Scope)

- [ ] Phase D: Autonomous acquisition pipeline (NYC commercial properties)
- [ ] Draft market memo generator
- [ ] Watchlist / custom ZIP alerts
- [ ] AI valuation model (AVM)
- [ ] Multi-user access
