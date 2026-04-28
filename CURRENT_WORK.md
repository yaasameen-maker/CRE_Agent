# Current Work — CRE Signal Agent

**Last updated:** 2026-04-28
**Sprint day:** 1 of 8

---

## Phase A: Demo Build (Days 1–4, through 2026-05-01)

Goal: Prove the pipeline works. 3 data sources (FRED, BLS, RentCast), thin LLM adapter + OpenRouter, `python run_demo.py` producing a ranked digest and one opportunity brief.

| Owner | Task | Status | Branch |
|-------|------|--------|--------|
| Beatrice | DevSecOps pipeline + project docs | Done | feat/devsecops-pipeline |
| Beatrice | Push to GitHub + branch protection | Up next | — |
| Beatrice | LLM abstraction layer (thin adapter + OpenRouter) | Day 2 | — |
| Beatrice | FRED + BLS + RentCast MCP servers | Day 2–3 | — |
| Beatrice | Bronze layer (SQLite cache for 3 sources) | Day 2–3 | — |
| Beatrice | Silver layer (ZIP normalization, 30-day window) | Day 3 | — |
| Beatrice | Gold layer (signal scoring, ranked digest) | Day 3–4 | — |
| Beatrice | Brief generator (1 brief per top signal) | Day 4 | — |
| Beatrice | `run_demo.py` script | Day 4 | — |
| Yaasameen | Frontend scaffold | Day 2 | — |
| Both | Shared JSON schema (`docs/schema/`) | Day 2 | — |

---

## Architecture Pivot (Saturday 2026-05-02)

Claude API key arrives. Thin adapter replaced with Strands. Prompt caching activates automatically.

| Owner | Task | Status |
|-------|------|--------|
| Beatrice | Add `ANTHROPIC_API_KEY` to `.env`, set `LLM_PROVIDER=anthropic` | Saturday |
| Beatrice | Delete `src/llm/adapter.py`, `openrouter.py`, `anthropic.py` | Saturday |
| Beatrice | Create `src/agents/signal_agent.py` (Strands Agent) | Saturday |
| Beatrice | Smoke test end-to-end | Saturday |

Phase B does not begin until pivot is confirmed working.

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

- DevSecOps pipeline: pre-commit, CI, security workflows, PR template, CODEOWNERS, CONTRIBUTING.md
- All project documentation: CLAUDE.md, AGENTS.md, ROADMAP.md, NOTES.md, ARCHITECTURE.md, KNOWLEDGE.md, CURRENT_WORK.md
- Architecture decisions finalized: thin adapter Phase A, Strands pivot Saturday
