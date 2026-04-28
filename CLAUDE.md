# CRE Signal Agent — Claude Code Guide

AI-powered commercial real estate distress signal scorer. Ingests public data, scores via Claude API, delivers a daily ranked digest before 8am.

## Team

- **Beatrice** — backend (`src/`). Uses Claude Code.
- **Yaasameen** — frontend (`frontend/`). Uses non-Claude agents.

Do not touch `frontend/` — that is Yaasameen's domain.

## Branch Naming

CI enforces these prefixes. PRs from branches that don't match will fail the branch-check workflow.

- `feat/*` — new features
- `fix/*` — bug fixes
- `doc/*` — documentation only
- `hotfix/*` — emergency fixes to main

## Commit Message Format

```
feat: short description
fix: short description
docs: short description
chore: short description
test: short description
refactor: short description
```

One line. Imperative mood. No period at the end.

## Tests

Every function in `src/` must have a corresponding test in `tests/unit/`. Run before committing:

```bash
pytest tests/unit/
```

Run integration tests separately (they hit real SQLite and may require env vars):

```bash
pytest tests/integration/
```

## Pre-Commit

Run before pushing:

```bash
pre-commit run --all-files
```

Hooks: ruff (lint + format), mypy, bandit, detect-secrets. If a hook fails, fix the code — do not use `--no-verify` once `src/` exists.

## MCP Servers

`src/mcp/` contains one MCP server per data source. Data access always goes through the MCP layer — never call external APIs (FRED, ATTOM, RentCast, BLS, FHFA, Census, HUD) directly from business logic.

Each MCP server:
1. Exposes tools via the `@tool` decorator pattern (auto-generates the JSON schema Claude sees)
2. Caches every response to the Bronze SQLite layer before returning — never make a duplicate API call

```
src/mcp/
  fred.py       # get_delinquency_rate(series_id)
  attom.py      # get_foreclosure_filings(zip_code, days_back), get_deed_transfers(zip_code, days_back)
  rentcast.py   # get_rent_trend(zip_code), get_vacancy_rate(zip_code)
  bls.py        # get_employment_trend(metro_code)
  fhfa.py       # get_price_index(metro_code)
  census.py     # get_demographics(census_tract)
  hud.py        # get_hud_vacancy(metro_code)
```

## Build Phases — Architecture Matters Here

This project builds in two phases. Understand which phase you're in before writing code.

- **Phase A (Days 1–4, through Friday):** Thin adapter in `src/llm/`. Proves the pipeline works. OpenRouter.
- **Saturday pivot:** Thin adapter replaced by Strands. Claude API key activates. `src/agents/` is created. `src/llm/adapter.py`, `openrouter.py`, `anthropic.py` are deleted.
- **Phase B (Days 5–8):** Strands agentic loop. All 7 MCP servers. Full pipeline.

During Phase A, `src/llm/` is the LLM entry point. During Phase B, `src/agents/signal_agent.py` is the entry point. `src/mcp/` and `src/prompts/` are unchanged across both phases.

## LLM Abstraction Layer (Phase A — Demo)

`src/llm/` contains a thin adapter. During Phase A, never call OpenRouter directly from business logic. Always route through the adapter:

```python
from src.llm.adapter import LLMAdapter
```

- **Now through Friday:** `OpenRouterAdapter` is active (`LLM_PROVIDER=openrouter`)
- **Saturday 2026-05-02:** This entire layer is replaced by Strands. See the Strands section below.

## Strands Agent (Phase B — Full MVP)

After the Saturday pivot, `src/llm/` is deleted and replaced by `src/agents/`:

```python
from src.agents.signal_agent import signal_agent
result = signal_agent("Score distress signals for ZIP codes: 10001, 33101, 60601")
```

The agent has the system prompt, all 9 MCP tools, and the model baked in. Do not instantiate it more than once — treat it as a singleton in the pipeline.

## Prompt Caching

Static system prompts (scoring context, signal thresholds, domain knowledge) must use `cache_control`. Use the helpers in `src/llm/cache.py`. Do not skip this — it is designed in from day 1 so the Saturday API switch activates caching automatically.

OpenRouter silently ignores `cache_control`. That is expected and fine.

## Structured Outputs

Use Claude tool use with `tool_choice` forced to a specific tool name for any scored or structured data output. Example:

```python
tool_choice={"type": "tool", "name": "score_signals"}
```

Do not parse free-text LLM responses for structured data anywhere in the codebase.

## Database

- Location: `data/cre_signal.db`
- The `data/` directory is gitignored. Do not commit the database file.
- Schema migrations go in `data/migrations/` (this directory is tracked).
- Medallion layers: Bronze (raw API cache) → Silver (normalized) → Gold (scored + ranked).

## Secrets

- Never hardcode API keys, tokens, or credentials.
- Use environment variables. Load from `.env` via `python-dotenv`.
- `.env` is gitignored. Never commit it.
- Required env vars: `LLM_PROVIDER`, `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `SENDGRID_API_KEY`, `SLACK_BOT_TOKEN`.
