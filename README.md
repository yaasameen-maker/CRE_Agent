# CRE Signal Agent

AI tool that ingests public commercial real estate data, scores distress signals via a parallel multi-agent loop, and delivers a ranked digest before 8am daily.

**Status:** Phase B in progress (Day 8 of 8, 2026-05-05) | Phase A complete 2026-05-01

---

## What It Does

Pulls data from 7 public sources (FRED, ATTOM, RentCast, BLS, FHFA, Census ACS, HUD), scores five distress signals per ZIP code (vacancy, rent, price growth, employment, foreclosure activity), and produces:

- A ranked digest of the top 5–10 distressed markets
- Per-ZIP opportunity briefs with cited source data
- Model / Monitor / Ignore action alerts
- 8am email (SendGrid) + Slack delivery

---

## Architecture

### Agent Loop (Phase B)

```
OUTER LOOP: APScheduler — CronTrigger(hour=8, ET)
                         │
                         ▼
            COORDINATOR AGENT
            receives: MONITOR_ZIP_CODES
            ThreadPoolExecutor → N parallel sub-agents
         │          │          │          │
         ▼          ▼          ▼          ▼
   [SUB-AGENT] [SUB-AGENT] [SUB-AGENT] [SUB-AGENT]
   ZIP 10001   ZIP 33101   ZIP 60601   ZIP ...
   Pattern 3   Pattern 3   Pattern 3   Pattern 3
   Perceive    Perceive    Perceive    Perceive
   Think       Think       Think       Think
   Act         Act         Act         Act
   ├ fred      ├ fred      ├ fred      ├ fred
   ├ bls       ├ bls       ├ bls       ├ bls
   └ rentcast  └ rentcast  └ rentcast  └ rentcast
   Observe     Observe     Observe     Observe
   Adjust ↺   Adjust ↺   Adjust ↺   Adjust ↺
   GoldRecord  GoldRecord  GoldRecord  GoldRecord
         │          │          │          │
         └──────────┴──────────┴──────────┘
                         │
              AGGREGATION: build_digest()
              rank all GoldRecords → gold_digest table
                         │
                         ▼
            EXECUTION AGENT
            reads: ranked Gold layer digest
            score >= 70  → MODEL   → brief + SendGrid + Slack
            score 40-69  → MONITOR → Slack ping
            score <  40  → IGNORE  → log only
```

### Agent Pattern Selection

| Pattern | When | This codebase |
|---------|------|---------------|
| Single agent, deep loop | One subject, deep reasoning | One ZIP due-diligence |
| **Coordinator + parallel sub-agents** | **Many tasks, same type** | **Daily screen (50+ ZIPs)** |
| Orchestrator + dependent sub-agents | Tasks with dependencies | Brief needs prior context |
| Medallion pipeline + one agent | Mixed signals, many sources | All 7 sources → execution agent |

### Medallion Data Flow

```
Public APIs → MCP servers (src/mcp/) → Bronze SQLite cache
                                              │
                                        Silver layer (normalize_zip)
                                              │
                                         Gold layer (score_zip)
                                              │
                                       Execution agent
                                       (classify + deliver)
```

Each data source is wrapped in an MCP server (`src/mcp/`). Claude never calls external APIs directly — it calls registered tools. Every API response is cached to SQLite on first fetch.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system diagram and design decisions.

---

## Team

| Person | Role |
|--------|------|
| Beatrice | Backend: pipeline, MCP servers, scoring, delivery |
| Yaasameen | Frontend: dashboard, digest list, brief detail view |

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Set up environment
cp .env.example .env
# Phase A: add OPENROUTER_API_KEY
# Phase B: add ANTHROPIC_API_KEY, set LLM_PROVIDER=anthropic

# Run one-shot demo (Phase A / smoke test)
python run_demo.py --zips 10001,60601,90210

# Run monitor daemon — executes one cycle now, then waits for 8am daily
LLM_PROVIDER=anthropic python run_monitor.py --run-now

# Run monitor daemon — scheduled only, no immediate cycle
LLM_PROVIDER=anthropic python run_monitor.py
```

Supported ZIP codes: `10001` (NYC), `33101` (Miami), `60601` (Chicago), `90210` (LA).

---

## Development

```bash
# Install pre-commit hooks
pre-commit install --install-hooks

# Run tests
pytest tests/unit/
pytest tests/integration/

# Lint + format
ruff check src/ tests/
ruff format src/ tests/

# Type check
mypy src/
```

All branches must use `feat/*`, `fix/*`, `doc/*`, or `hotfix/*` prefixes. CI enforces this.

---

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

---

## Data Sources

FRED · ATTOM · RentCast · BLS · Census ACS · FHFA · HUD

All responses cached in Bronze layer on first fetch. Rate-limited sources (RentCast: 50 calls/month) are never called twice for the same data.

---

## Current Status

**Phase A (complete):**
- Bronze, Silver, and Gold layers implemented for the 3-source slice (FRED, BLS, RentCast)
- Opportunity brief generation for the top-ranked ZIP
- `run_demo.py` CLI orchestrates Bronze → Silver → Gold → Brief
- 125 passing tests across unit and integration coverage

**Phase B (in progress):**
- `AnthropicAdapter` — direct Anthropic API, activates prompt caching automatically
- `src/agents/signal_agent.py` — Strands Agent singleton with all MCP tools registered
- `src/agents/coordinator.py` — `ThreadPoolExecutor` runs one sub-agent per ZIP in parallel
- `src/agents/execution_agent.py` — classifies Gold records, dispatches briefs + delivery
- `src/agents/monitor.py` — APScheduler 8am `CronTrigger`
- `run_monitor.py` — daemon entry point (`--run-now` flag for smoke testing)
- `src/pipeline/action.py` — `ActionClassification` enum with Model/Monitor/Ignore thresholds
- `src/pipeline/delivery.py` — SendGrid + Slack stubs (skip-safe until keys arrive)

**Remaining (Beatrice):**
- ATTOM, FHFA, Census ACS, HUD MCP servers
- 7-signal Silver/Gold expansion
- SendGrid email template + Slack `post_message` implementation
- End-to-end integration test + demo prep
