# Build Notes — CRE Signal Agent

## 2026-05-02 — Day 5 (Saturday): Architecture Pivot Begins

**Status:** Phase A complete and all 11 tasks merged to main. Saturday pivot to Strands is in progress. Demo ZIPs produce ranked digest + opportunity brief. Frontend scaffold ready. Backend verification: 125 passing tests.

### Phase A Shipped
All tasks merged:
- PR #1: DevSecOps pipeline + project docs
- PR #2: LLM abstraction layer (thin adapter + OpenRouter)
- PR #3: MCP servers (FRED, BLS, RentCast) + Bronze cache
- PR #4: Backend closeout (Silver, Gold, brief generator, demo runner)
- PR #5: Frontend scaffold + shared schema

### Saturday Pivot (In Progress)
Replacing `src/llm/` thin adapter with Strands Agents SDK:
- Delete: `src/llm/adapter.py`, `openrouter.py`, `anthropic.py`
- Add: `src/agents/signal_agent.py` with Strands Agent wiring
- Set: `LLM_PROVIDER=anthropic`, add `ANTHROPIC_API_KEY`
- Test: Smoke test `python run_demo.py` to confirm Strands produces same output as OpenRouter Phase A

### Next Steps
1. Implement Strands pivot (Saturday AM/PM)
2. Smoke test with same demo ZIPs as Phase A to confirm output matches
3. Once pivot confirmed working, begin Phase B (Day 5 PM onwards):
   - ATTOM, FHFA, Census ACS, HUD MCP servers
   - Full 7-signal scoring via Strands
   - Delivery pipeline (8am trigger, SendGrid, Slack)

---

## 2026-05-01 — Day 4: Phase A Closed Out

**Status:** Bronze, Silver, Gold, brief generation, and the Phase A demo runner are now implemented for the 3-source slice. Backend verification is green with 125 passing unit and integration tests.

### What's Done
- Silver layer completed: ZIP normalization, 30-day freshness gating, null handling
- Gold layer completed: `score_signals` tool-call parsing fixed, ranked digest generation working
- Brief generation completed: typed opportunity brief output plus Markdown rendering
- Demo runner completed: `python run_demo.py --zips ...` now orchestrates Bronze → Silver → Gold → Brief
- Integration coverage added for end-to-end demo orchestration with temp SQLite

### Demo Status
- Supported demo ZIPs: `10001`, `33101`, `60601`, `90210`
- Unsupported ZIPs fail fast with a clear supported list
- Partial success is allowed as long as at least one ZIP produces a Gold record

### Next Milestone
- Saturday 2026-05-02: Architecture pivot to Strands Agents SDK
- Smoke-test `python run_demo.py` after the pivot before any Phase B feature work

---

## 2026-04-30 — Day 3: Phase A Momentum

**Status:** 3 PRs merged, 85 unit tests passing. Bronze layer fully operational with FRED, BLS, and RentCast MCP servers. All API responses cached to SQLite.

### What's Done
- PR #1: DevSecOps pipeline (CI, pre-commit, security scanning, branch protection)
- PR #2: LLM abstraction layer (`src/llm/adapter.py`, `OpenRouterAdapter`, `cache.py`, `SCORING_SYSTEM_PROMPT` stub)
- PR #3: MCP servers + Bronze cache (`src/mcp/{fred,bls,rentcast}.py`, `src/mcp/_db.py`, `data/migrations/001_bronze_schema.sql`)

### In Progress (Days 3–4)
- Silver layer: ZIP normalization, 30-day rolling window, null handling
- Gold layer: Signal scoring (vacancy, rent trend, employment trend thresholds)
- Brief generator: 1 opportunity brief per top signal
- Demo script: `python run_demo.py --zips 10001,33101,60601`

### Next Milestone
- End of Day 4 (2026-05-01): Phase A complete, all tests passing, demo produces ranked digest + 1 brief
- Saturday 2026-05-02: Architecture pivot to Strands Agents SDK (thin adapter replaced, Claude API activates)

---

## 2026-04-28 — Day 1 (continued): Architecture Pivot Decision

### Strands Agents SDK — Adopted for Phase B (Saturday 2026-05-02)

After reviewing the full Strands SDK, we decided to use it — but not yet.

**Decision:** Build Phase A (Days 1–4) with a thin custom adapter + OpenRouter. On Saturday 2026-05-02 when the Claude API key arrives, replace the thin adapter with Strands. Phase B (Days 5–8) runs on the full Strands agentic loop.

**Why not Strands from Day 1:**
- Strands doesn't speak OpenRouter natively. You'd need LiteLLM as a bridge, which adds another dependency and makes the Saturday swap harder, not easier.
- An 8-day sprint is too short to debug an SDK + a bridge + business logic at the same time.
- Thin adapter is ~50 lines. Strands is hundreds of lines of framework to learn.

**Why Strands on Saturday:**
- Native Claude API support — no bridge needed.
- Agentic loop (Perceive → Think → Act → Observe → Adjust) replaces manual scoring orchestration.
- Prompt caching activates automatically — `cache_control` blocks are already in the prompts.
- Native MCP tool integration — `src/mcp/` is completely unchanged.

**Refactor scope is small:**
- Delete: `src/llm/adapter.py`, `openrouter.py`, `anthropic.py`
- Add: `src/agents/signal_agent.py` (~50 lines)
- Unchanged: Bronze/Silver/Gold pipeline, all 7 MCP servers, delivery, all tests
- Estimated effort: ~150–200 lines changed, ~4–6 hours

**What changes in Phase A to make Saturday easy:**
- System prompts live in `src/prompts/scoring.py` as standalone string constants — Strands reads them unchanged.
- Scoring functions have clean interfaces and don't touch the LLM adapter directly.
- `@tool` decorated MCP functions are already in the exact format Strands expects.

---

## 2026-04-27 — Day 1

### Decisions Made
- LLM stack: OpenRouter (Claude model) for Days 1–4, switch to direct Anthropic Claude API on Saturday 2026-05-02 when key arrives. One env var change.
- Abstraction: thin custom adapter in src/llm/. Rejected Strands (too heavy for 8-day sprint) and LiteLLM (extra dependency for a problem we can solve in ~50 lines).
- Prompt caching: baked in from day 1. Static system prompts (scoring context, thresholds) get cache_control. OpenRouter ignores it; Claude API will use it.
- Structured outputs: Claude tool_use with forced tool_choice for scoring. No free-text parsing — models the behavior the PRD called "future iteration" but it's simpler than the alternative.
- Database: SQLite at data/cre_signal.db. Local demo only. Postgres path is easy if needed later.
- Entity resolution: ZIP-code level for MVP. No geocoding layer yet.
- Time alignment: rolling 30-day window. Percentage change vs prior period.
- Medallion architecture: Bronze (raw API cache in SQLite) → Silver (normalized, ZIP-aligned) → Gold (scored, ranked). Frontend reads Gold only.
- Scheduler: APScheduler (in-process). Cron if ever deployed to a server.

### Progress
- DevSecOps pipeline complete: pre-commit hooks, CI workflows (ci.yml, security.yml, branch-check.yml), PR template, CODEOWNERS, CONTRIBUTING.md
- Project documentation files created

### PRD Cross-Reference (Yaasameen's PRD v1.0)
- **MCP Servers adopted:** All 7 data sources wrapped in MCP servers (`src/mcp/`). Replaces direct httpx API calls. Each server caches to Bronze on every call.
- **Thin custom adapter confirmed:** Rejected Strands Agents SDK despite Yaasameen's PRD specifying it — team agreed thin adapter is right for 8-day scope.
- **HUD added as 7th source:** Original PRD had 6 sources. Yaasameen's PRD adds HUD (huduser.gov) for vacancy surveys.
- **Market memo moved to Post-MVP:** Yaasameen's PRD lists it as P2/Nice-to-have. Removed from 8-day ROADMAP.
- **Sequential build confirmed:** Phase 2 (signal scoring) cannot start until Phase 1 pipeline is stable and returning clean data from all 7 sources.

### Open Questions
- Confirm Yaasameen's frontend tech stack (React? Next.js?) so AGENTS.md and schema docs can be more specific.
