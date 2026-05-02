# CRE Signal Agent — Roadmap

**Sprint:** 2026-04-28 to 2026-05-06 (8 working days)
**Repo:** https://github.com/b-mackenzie-alexander/CRE_Agent

---

## Phase A: Demo Build — Prove It Works (Days 1–4, through 2026-05-01)

Goal: End-to-end pipeline running with 3 data sources, scored by Claude via OpenRouter, producing a ranked digest and one opportunity brief. Thin adapter architecture — gets replaced Saturday.

- [x] DevSecOps pipeline (CI, pre-commit, branch protection) `[Beatrice]`
- [x] Project documentation (CLAUDE.md, AGENTS.md, ARCHITECTURE.md, ROADMAP.md, etc.) `[Beatrice]`
- [x] LLM abstraction layer — thin adapter + OpenRouter adapter `[Beatrice]` (PR #2)
- [x] MCP servers: FRED, BLS, RentCast (3 of 7) `[Beatrice]` (PR #3)
- [x] Bronze layer: SQLite cache for 3 sources `[Beatrice]` (PR #3 — 001_bronze_schema.sql, 85 unit tests)
- [x] Silver layer: ZIP normalization, 30-day window, null handling `[Beatrice]`
- [x] Gold layer: signal scoring (3 signals), ranked digest `[Beatrice]`
- [x] Brief generator: one opportunity brief per top signal `[Beatrice]`
- [x] Demo run script: `python run_demo.py --zips <zip1,zip2,zip3>` `[Beatrice]`
- [ ] Frontend scaffold (project setup, routing, layout) `[Yaasameen]`
- [ ] Shared JSON schema definition `[Both]`

---

## Architecture Pivot (Saturday 2026-05-02)

Claude API key arrives. Thin adapter replaced with Strands. Prompt caching activates automatically. This happens AFTER Phase A is complete and smoke-tested.

- [ ] Set `LLM_PROVIDER=anthropic`, add `ANTHROPIC_API_KEY` to `.env` `[Beatrice]` **← Day 4 or 5**
- [ ] Replace `src/llm/` adapter with Strands Agents SDK `[Beatrice]`
- [ ] Create `src/agents/signal_agent.py` — Strands Agent wiring model + system prompt + MCP tools `[Beatrice]`
- [ ] Confirm prompt caching active (cache_control blocks built in from day 1, now live) `[Beatrice]`
- [ ] Smoke test end-to-end before beginning Phase B `[Beatrice]`

> **Phase B does not begin until:** Phase A is complete (now done), Saturday 2026-05-02 pivot is confirmed working, and full test suite passes after the Strands migration smoke test.

---

## Phase B: Full MVP (Days 5–8, 2026-05-02 to 2026-05-06)

Goal: All 7 data sources, full Strands agentic loop, delivery pipeline, frontend integrated.

### Backend `[Beatrice]`

- [ ] Remaining MCP servers: ATTOM, FHFA, Census ACS, HUD `[Beatrice]`
- [ ] Full 7-signal scoring via Strands agent `[Beatrice]`
- [ ] Complete brief generation + action alert logic (Model / Monitor / Ignore) `[Beatrice]`
- [ ] APScheduler: 8am daily trigger `[Beatrice]`
- [ ] SendGrid email digest template `[Beatrice]`
- [ ] Slack digest integration `[Beatrice]`

### Frontend `[Yaasameen]`

- [ ] Digest list view (reads Gold layer JSON) `[Yaasameen]`
- [ ] Opportunity card component `[Yaasameen]`
- [ ] Brief detail view `[Yaasameen]`
- [ ] Action alert display `[Yaasameen]`

### Integration `[Both]`

- [ ] End-to-end integration test `[Both]`
- [ ] Demo preparation `[Both]`

---

## Post-MVP (Out of Sprint Scope)

- [ ] Draft market memo generator (Claude → analyst-ready narrative) `[Beatrice]`
- [ ] Watchlist / custom ZIP alerts `[Both]`
- [ ] AI valuation model (AVM) `[Both]`
- [ ] Multi-user access `[Both]`
