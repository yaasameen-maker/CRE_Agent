# Build Notes — CRE Signal Agent

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
- What ZIP codes should we target for the demo? Need to pick 3–5 markets to constrain API usage.
- RentCast free tier = 50 calls/month. What's the minimum ZIP set that makes a compelling demo?
- Confirm Yaasameen's frontend tech stack (React? Next.js?) so AGENTS.md and schema docs can be more specific.
