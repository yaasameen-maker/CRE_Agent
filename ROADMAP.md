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

## Phase B: Full MVP (Days 5–8, 2026-05-02 to 2026-05-06)

### Block 0 — Documentation Reset ✅ COMPLETE
- [x] ROADMAP.md — updated checklist
- [x] CURRENT_WORK.md — Day 7 actual state
- [x] ARCHITECTURE.md — Yaasameen V2 agent architecture
- [x] README.md — current state and quick start
- [x] NOTES.md + KNOWLEDGE.md — session entries

### Block 1 — Strands Agent Layer (gates everything)
- [ ] `src/agents/signal_agent.py` — Strands Agent, one ZIP, forced tool use scoring
- [ ] `src/agents/coordinator.py` — asyncio.gather N signal_agent calls in parallel
- [ ] `src/agents/execution_agent.py` — Model/Monitor/Ignore classification + delivery dispatch
- [ ] `src/agents/monitor.py` — APScheduler 8am CronTrigger(hour=8, ET)
- [ ] Add ANTHROPIC_API_KEY to .env, set LLM_PROVIDER=anthropic
- [ ] Smoke test run_demo.py end-to-end with Anthropic key
- [ ] All 124 existing tests pass after pivot

### Block 2 — Pipeline Extensions
- [ ] `src/pipeline/action.py` — ActionClassifier + ActionLabel enum (MODEL/MONITOR/IGNORE)
- [ ] `src/pipeline/delivery.py` — SendGrid email digest + Slack post_message

### Block 3 — 4 New MCP Servers
- [ ] `src/mcp/attom.py` — get_foreclosure_filings, get_deed_transfers (HIGH)
- [ ] `src/mcp/fhfa.py` — get_price_index (MEDIUM)
- [ ] `src/mcp/census.py` — get_demographics (MEDIUM)
- [ ] `src/mcp/hud.py` — get_hud_vacancy (MEDIUM)
- [ ] Unit tests for all 4

### Block 4 — 7-Signal Expansion
- [ ] `data/migrations/003_silver_gold_7signal.sql`
- [ ] Expand SilverRecord (4 new nullable fields) in normalizer.py
- [ ] Update scoring prompt for 7 signals in prompts/scoring.py
- [ ] Add new MCP tools to coordinator.py
- [ ] Update affected tests

### Block 5 — NYC Scope
- [ ] `src/pipeline/config.py` — NYC_ZIP_CODES frozenset, SCOPE_NYC_ONLY env toggle
- [ ] Scope filter in coordinator.py
- [ ] NYC demo ZIPs in demo.py

### Block 6 — Cleanup PR (after smoke test)
- [ ] Delete `src/llm/openrouter.py`, `src/llm/adapter.py`, `src/llm/__init__.py`
- [ ] Delete `tests/unit/llm/` directory
- [ ] Remove openrouter from requirements.txt

### Block 7 — Integration & Demo
- [ ] `tests/integration/test_full_pipeline.py` — full 7-source pipeline test
- [ ] All tests green before PR

---

## Post-MVP (Out of Sprint Scope)

- [ ] Phase C: Autonomous acquisition pipeline (NYC commercial properties)
- [ ] Draft market memo generator
- [ ] Watchlist / custom ZIP alerts
- [ ] AI valuation model (AVM)
- [ ] Multi-user access
