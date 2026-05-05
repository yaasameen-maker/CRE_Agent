# Current Work — CRE Signal Agent

**Last updated:** 2026-05-05
**Sprint day:** 7 of 8

---

## Phase A: Demo Build (Days 1–4, through 2026-05-01) ✅ COMPLETE

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
| Yaasameen | Action Alerts view | ✅ Merged | #8 | — |
| Yaasameen | Opportunity Brief detail view | ✅ Merged | #9 | — |

**Backend verification: 124 passing tests.** Frontend has Action Alerts and Opportunity Brief views complete. Phase A proves the pipeline works end-to-end.

---

## Architecture Pivot — IN PROGRESS

Yaasameen's V2 agent design adopted. `src/agents/` not yet built. The coordinator/subagent architecture replaces the original single `signal_agent.py` plan.

Target structure:
```
src/agents/
  signal_agent.py      # Strands Agent, scores one ZIP, forced tool use
  coordinator.py       # asyncio.gather N signal_agent calls in parallel
  execution_agent.py   # Model/Monitor/Ignore classification + delivery dispatch
  monitor.py           # APScheduler CronTrigger(hour=8, ET)
```

---

## Phase B: Full MVP (Days 5–8) — IN PROGRESS

### Block 1 — Strands Agent Layer (gates everything)
| Task | Status |
|------|--------|
| `src/agents/signal_agent.py` — Strands Agent, one ZIP | Not started |
| `src/agents/coordinator.py` — asyncio.gather N signal_agents | Not started |
| `src/agents/execution_agent.py` — classification + delivery dispatch | Not started |
| `src/agents/monitor.py` — APScheduler 8am trigger | Not started |
| Add ANTHROPIC_API_KEY to .env, set LLM_PROVIDER=anthropic | Not started |
| Smoke test run_demo.py end-to-end | Not started |
| All 124 existing tests pass after pivot | Not started |

### Block 2 — Pipeline Extensions
| Task | Status |
|------|--------|
| `src/pipeline/action.py` — ActionClassifier + ActionLabel enum | Not started |
| `src/pipeline/delivery.py` — SendGrid email + Slack | Not started |

### Block 3 — 4 New MCP Servers
| Task | Status |
|------|--------|
| `src/mcp/attom.py` — get_foreclosure_filings, get_deed_transfers | Not started |
| `src/mcp/fhfa.py` — get_price_index | Not started |
| `src/mcp/census.py` — get_demographics | Not started |
| `src/mcp/hud.py` — get_hud_vacancy | Not started |

### Block 4 — 7-Signal Expansion
| Task | Status |
|------|--------|
| `data/migrations/003_silver_gold_7signal.sql` | Not started |
| Expand SilverRecord (4 new nullable fields) in normalizer.py | Not started |
| Update scoring prompt for 7 signals | Not started |
| Add new MCP tools to coordinator.py | Not started |

### Block 5 — NYC Scope
| Task | Status |
|------|--------|
| `src/pipeline/config.py` — NYC_ZIP_CODES frozenset, SCOPE_NYC_ONLY toggle | Not started |
| Scope filter in coordinator.py | Not started |
| NYC demo ZIPs in demo.py | Not started |

### Block 7 — Integration & Demo
| Task | Status |
|------|--------|
| `tests/integration/test_full_pipeline.py` | Not started |
| All tests green before PR | Not started |

---

## Recently Completed

### 2026-05-05 — Documentation reset
- Docs updated to reflect Day 7 actual state
- Yaasameen's V2 architecture adopted: coordinator → N signal_agents → execution_agent
- Director requirement captured: NYC scope narrowing + Phase C (future sprint)

### 2026-05-04 — Yaasameen: Action Alerts + Opportunity Brief views merged (PRs #8, #9)
- Action Alerts view now renders Model/Monitor/Ignore classifications from Gold layer JSON
- Opportunity Brief detail view renders per-ZIP brief content

### 2026-05-02 — Phase A complete and merged to main
- All 11 Phase A tasks shipped: DevSecOps, LLM abstraction, 3 MCP servers, Bronze/Silver/Gold layers, brief generation, demo runner, frontend scaffold, schema
- 124 passing tests across unit and integration coverage
- Demo ZIPs working: `10001`, `33101`, `60601`, `90210` produce ranked digest + opportunity brief
