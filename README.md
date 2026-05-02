# CRE Signal Agent

AI tool that ingests public commercial real estate data, scores distress signals, and delivers a ranked digest before 8am daily.

**Status:** Sprint active — Phase A complete and merged (2026-04-28 to 2026-05-01), Phase B begins after Strands pivot | **Today:** Day 5 of 8, Saturday (2026-05-02)

---

## What It Does

Pulls data from 7 public sources (FRED, ATTOM, RentCast, BLS, FHFA, Census ACS, HUD), scores five distress signals per ZIP code (vacancy, rent, price growth, employment, foreclosure activity), and produces:

- A ranked digest of the top 5–10 distressed markets
- Per-ZIP opportunity briefs with cited source data
- Model / Monitor / Ignore action alerts
- 8am email (SendGrid) + Slack delivery

## Architecture

Bronze (raw API cache) → Silver (ZIP-normalized, 30-day window) → Gold (scored, ranked) → LLM → Delivery

Each data source is wrapped in an MCP server (`src/mcp/`). Claude never calls external APIs directly — it calls registered tools. Every API response is cached to SQLite on first fetch.

**Phase A (completed 2026-05-01, merged to main):** Thin adapter + OpenRouter — pipeline, digest, brief, and demo runner are in place.  
**Saturday 2026-05-02 (now):** Thin adapter replaced with Strands Agents SDK when Claude API key arrives — **next task**.  
**Phase B (2026-05-02–2026-05-06):** Full Strands agentic loop, all 7 sources, delivery, frontend integrated.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system diagram and design decisions.

## Team

| Person | Role |
|--------|------|
| Beatrice | Backend: pipeline, MCP servers, scoring, delivery |
| Yaasameen | Frontend: dashboard, digest list, brief detail view |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Set up environment
cp .env.example .env
# Add OPENROUTER_API_KEY (Phase A) or ANTHROPIC_API_KEY (Phase B)

# Run demo (Phase A)
python run_demo.py --zips 10001,60601,90210
```

Supported demo ZIPs are currently `10001`, `33101`, `60601`, and `90210`.

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

**Phase A: Complete and merged to main**
- Bronze, Silver, and Gold layers fully implemented for the 3-source slice (FRED, BLS, RentCast)
- Opportunity brief generation with Markdown rendering implemented
- `run_demo.py` orchestrates Bronze → Silver → Gold → Brief for supported demo ZIPs (`10001`, `33101`, `60601`, `90210`)
- Backend verification: **125 passing tests** across unit and integration coverage
- Frontend scaffold complete: React/Vite/TS, routing, layout, shared JSON schema definitions

**Phase B: Pending Strands pivot (Saturday 2026-05-02)**
- Replace `src/llm/` thin adapter with Strands Agents SDK
- Activate Claude API key (`ANTHROPIC_API_KEY`)
- Remaining 4 MCP servers: ATTOM, FHFA, Census ACS, HUD
- Full 7-signal scoring via Strands agentic loop
- Delivery pipeline: APScheduler (8am trigger), SendGrid email, Slack digest
