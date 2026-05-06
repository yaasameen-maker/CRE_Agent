# CRE Signal Agent

AI tool that ingests public commercial real estate data, scores distress signals, and delivers a ranked digest before 8am daily.

**Status:** Sprint active — Phase A complete and merged (PRs #1-5, #8, #9), Phase B in progress | **Today:** Day 7 of 8 (2026-05-05)

---

## What It Does

Pulls data from 7 public sources (FRED, ATTOM, RentCast, BLS, FHFA, Census ACS, HUD), scores five distress signals per ZIP code (vacancy, rent, price growth, employment, foreclosure activity), and produces:

- A ranked digest of the top 5–10 distressed markets
- Per-ZIP opportunity briefs with cited source data
- Model / Monitor / Ignore action alerts
- 8am email (SendGrid) + Slack delivery

## Architecture

Bronze (raw API cache) → Silver (ZIP-normalized, 30-day window) → Gold (scored, ranked) → Strands Agent Layer → Delivery

Each data source is wrapped in an MCP server (`src/mcp/`). Claude never calls external APIs directly — it calls registered tools. Every API response is cached to SQLite on first fetch.

**Phase A (completed 2026-05-01, merged to main):** Thin adapter + OpenRouter — pipeline, digest, brief, and demo runner are in place.
**Phase B (in progress, Day 7 of 8):** Strands agent layer (`src/agents/`) replaces the thin adapter. Coordinator/subagent design: one `signal_agent` per ZIP runs in parallel, `execution_agent` classifies (Model/Monitor/Ignore) and dispatches delivery. NYC scope with `SCOPE_NYC_ONLY` env toggle.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system diagram and design decisions.

## Team

| Person | Role |
|--------|------|
| Beatrice | Backend: pipeline, MCP servers, scoring, delivery, Strands agent layer |
| Yaasameen | Frontend: dashboard, digest list, brief detail view — Action Alerts (PR #8) and Opportunity Brief detail view (PR #9) complete |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Set up environment
cp .env.example .env
# Phase A demo: add OPENROUTER_API_KEY, set LLM_PROVIDER=openrouter
# Phase B (Strands): add ANTHROPIC_API_KEY, set LLM_PROVIDER=anthropic

# Run demo (Phase A — OpenRouter)
python run_demo.py --zips 10001,60601,90210
```

Phase A supported demo ZIPs: `10001`, `33101`, `60601`, `90210`. Phase B will expand to full NYC ZIP coverage via `src/pipeline/config.py`.

## Development

```bash
# Install pre-commit hooks
pre-commit install --install-hooks

# Run tests
pytest tests/unit/
pytest tests/integration/

# Run full backend regression suite
pytest tests/unit/ tests/integration/

# Lint + format
ruff check src/ tests/
ruff format src/ tests/

# Type check
mypy src/
```

All branches must use `feat/*`, `fix/*`, `doc/*`, or `hotfix/*` prefixes. CI enforces this.

## Docs

| File | Purpose |
|------|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System diagram, Medallion layers, design decisions |
| [ROADMAP.md](ROADMAP.md) | Sprint checklist with task ownership |
| [CURRENT_WORK.md](CURRENT_WORK.md) | Active tasks and sprint status |
| [CLAUDE.md](CLAUDE.md) | Agent conventions for Claude Code (Beatrice) |
| [AGENTS.md](AGENTS.md) | Agent conventions for Yaasameen's tools |
| [KNOWLEDGE.md](KNOWLEDGE.md) | Quirks and gotchas discovered during the build |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines |

## Data Sources

FRED · ATTOM · RentCast · BLS · Census ACS · FHFA · HUD

All responses cached in Bronze layer on first fetch. Rate-limited sources (RentCast: 50 calls/month) are never called twice for the same data.

## Current Phase Status

**Phase A: Complete and merged to main (PRs #1-5, #8, #9)**
- Bronze, Silver, and Gold layers fully implemented for the 3-source slice (FRED, BLS, RentCast)
- Opportunity brief generation with Markdown rendering implemented
- `run_demo.py` orchestrates Bronze → Silver → Gold → Brief for supported demo ZIPs (`10001`, `33101`, `60601`, `90210`)
- Backend verification: **124 passing tests** across unit and integration coverage
- Frontend complete: scaffold, routing, layout, shared JSON schema, Action Alerts view, Opportunity Brief detail view

**Phase B: In progress (Day 7 of 8)**
- `src/agents/` not yet built — Block 1 (Strands agent layer) is the current gating task
- Coordinator/subagent pattern: `coordinator.py` → N parallel `signal_agent.py` → `execution_agent.py`
- NYC scope: `SCOPE_NYC_ONLY` env toggle in `src/pipeline/config.py`
- Remaining 4 MCP servers: ATTOM, FHFA, Census ACS, HUD
- Delivery pipeline: APScheduler (8am), SendGrid email, Slack digest
