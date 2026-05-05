# Knowledge Base — CRE Signal Agent

Quirks, gotchas, and non-obvious things discovered during the build.

---

## Pre-Commit

**Exit code 5 from pytest on empty test directories is not a failure.**
pytest returns exit code 5 ("no tests collected") when a test directory is empty. Pre-commit treats this as a hook failure by default. Fix: pytest is configured with `--ignore` flags or the directories won't be empty once backend code exists. For now, if you run `pre-commit run pytest-unit --all-files` on an empty `tests/unit/`, it will show failure — that's expected until first tests are written.

**Use `--no-verify` only for infrastructure commits, never for code.**
During the DevSecOps setup phase, commits used `--no-verify` because `src/` didn't exist yet. Once `src/` exists, `--no-verify` is banned. If a hook fails, fix the code.

**Stage names must be `pre-commit`/`pre-push`, not `commit`/`push`.**
Pre-commit v4+ uses the longer names. The short names still work but produce deprecation warnings and will break in v5.

---

## detect-secrets

**Regenerate the baseline after adding any string that looks like a secret.**
If you add a config value, API endpoint URL, or test fixture that contains a long random-looking string, detect-secrets may flag it. Run `detect-secrets scan > .secrets.baseline` to update the baseline, then commit the updated baseline. This is not a security hole — you're acknowledging a known false positive.

**The baseline must be committed.**
`.secrets.baseline` is tracked in git. If it's missing, the CI secrets-scan job will fail.

---

## API Limits

**RentCast free tier = 50 calls/month.**
Cache every response in SQLite immediately. Never make the same call twice without checking the cache first. For the demo, constrain to 3–5 ZIP codes maximum.

**ATTOM sandbox has its own call limits.**
Check the ATTOM dashboard for current quota. Same rule: cache everything.

---

## LLM

**OpenRouter ignores `cache_control` — that's fine.**
The Anthropic `cache_control` field on messages is silently ignored by OpenRouter. Build the caching structure into prompts now so the switch to Claude API on Saturday activates it automatically.

**`OPENROUTER_API_KEY` is the env var name for the abstraction layer.**
The adapter reads `LLM_PROVIDER` (values: `openrouter` or `anthropic`) and the corresponding key (`OPENROUTER_API_KEY` or `ANTHROPIC_API_KEY`). Both must be in `.env`.

**Forced tool_choice gives you guaranteed JSON.**
When calling Claude with `tool_choice: {"type": "tool", "name": "score_signals"}`, the model is forced to return a valid tool_use block. This is the correct pattern for the scoring layer — do not use `tool_choice: "auto"` where structured output is required.

**Read structured outputs from `LLMResponse.tool_calls`, not `content`.**
The OpenRouter adapter normalizes tool calls into `LLMResponse.tool_calls`. The Gold scorer and brief generator should parse that field directly and treat missing tool calls as a hard failure.

---

## MCP Servers

**Every MCP tool must cache to Bronze before returning.**
The pattern is: check Bronze cache first → if hit, return cached row → if miss, call the external API, write to Bronze, return result. Never call ATTOM, RentCast, or any other rate-limited API without checking the cache first. This is already implemented in PR #3 for FRED, BLS, and RentCast. Apply the same pattern to ATTOM, FHFA, Census ACS, and HUD in Phase B.

**Current servers (PR #3):**
- `src/mcp/fred.py`: `get_delinquency_rate(series_id)` — FRED delinquency data cached to Bronze
- `src/mcp/bls.py`: `get_employment_trend(metro_code)` — BLS employment data cached to Bronze
- `src/mcp/rentcast.py`: `get_rent_trend(zip_code)`, `get_vacancy_rate(zip_code)` — RentCast data cached to Bronze

**Remaining servers (Phase B):**
- `src/mcp/attom.py`: `get_foreclosure_filings(zip_code, days_back)`, `get_deed_transfers(zip_code, days_back)`
- `src/mcp/fhfa.py`: `get_price_index(metro_code)`
- `src/mcp/census.py`: `get_demographics(census_tract)`
- `src/mcp/hud.py`: `get_hud_vacancy(metro_code)`

**HUD is the 7th data source — easy to miss.**
Early PRD drafts listed 6 sources (FRED, ATTOM, RentCast, BLS, Census, FHFA). Yaasameen's final PRD added HUD (huduser.gov) for office/residential vacancy trends. There should be 7 MCP servers total, not 6.

**The `@tool` decorator auto-generates the JSON schema Claude sees.**
Write clean type hints and a clear one-line docstring on every tool function — that becomes the contract Claude uses to decide when and how to call the tool. A vague docstring = Claude calling the tool incorrectly. See `src/mcp/fred.py` and `src/mcp/bls.py` for examples of well-documented tools.

---

## SQLite

**Database lives at `data/cre_signal.db`.**
The `data/` directory is gitignored. Do not commit the database. Schema migrations live in `data/migrations/` (tracked) and are applied on startup.

## Demo Runner

**Phase A demo ZIP support is intentionally small.**
`run_demo.py` currently supports `10001`, `33101`, `60601`, and `90210` through a built-in ZIP mapping. Unsupported ZIPs should fail fast with the supported list instead of guessing metro or FRED identifiers.

**Partial demo success is acceptable.**
If one ZIP fails normalization or scoring, the demo should continue for the remaining ZIPs and still emit a digest and brief if at least one Gold record was produced.

---

## Agent Architecture (Phase B)

**Yaasameen's V2 coordinator/subagent design was adopted for Phase B.**
The original plan had a single `signal_agent.py` scoring all ZIPs sequentially. V2 splits this into: a `coordinator.py` that runs one `signal_agent` per ZIP in parallel (via `asyncio.gather`), feeding results to an `execution_agent.py` for classification and delivery dispatch. Adopted because it better matches the real-world runtime pattern (ZIP-level parallelism) and maps cleanly to the Model/Monitor/Ignore delivery tiers.

**`execution_agent.py` classification thresholds:**
- MODEL (≥ 70): opportunity brief + email digest + Slack alert
- MONITOR (40–69): watchlist entry + Slack notification
- IGNORE (< 40): log only, no delivery

**Agent files in `src/agents/` are all Beatrice's scope.**
Yaasameen drafted the design but the backend agent files (signal_agent.py, coordinator.py, execution_agent.py, monitor.py) were not pushed to the repo — they are absorbed into Beatrice's Phase B implementation scope.

---

## NYC Scope Narrowing

**SCOPE_NYC_ONLY is an env toggle, not hardcoded.**
The director requirement to focus on NYC commercial real estate is implemented as a runtime toggle (`SCOPE_NYC_ONLY=true` in `.env`) in `src/pipeline/config.py`. The ZIP set is a frozenset constant (`NYC_ZIP_CODES`) in that file. When the toggle is off, the coordinator accepts any ZIP — this allows future geographic expansion without a code change.

**Do not hardcode NYC filtering inside coordinator.py or signal_agent.py.**
The scope filter lives only in `config.py` and is applied at the coordinator input boundary.

---

## Phase C (Autonomous Acquisition) — Out of Sprint Scope

**Phase C is a future sprint, not Phase B.**
The director outlined a Phase C involving autonomous acquisition pipeline for NYC commercial properties. This has its own spec and is explicitly out of the current 8-day sprint scope. Do not scope-creep Phase B to include Phase C features. Record it in ROADMAP.md Post-MVP section only.

---

## Strands Migration (Phase A → Phase B, Saturday 2026-05-02 — IN PROGRESS)

**Strands doesn't speak OpenRouter — that's why Phase A uses a thin adapter.**
Strands has native Anthropic API support but requires LiteLLM as a bridge for OpenRouter. Using a bridge adds complexity and makes the Saturday swap harder. The thin adapter was the right call for Days 1–4.

**The refactor is small by design.**
Everything in Phase A is structured to make the Saturday swap a one-day job:
- `src/prompts/scoring.py` — standalone string constants, Strands reads them unchanged
- `src/mcp/*.py` — `@tool` decorated functions in exactly the format Strands expects
- `src/llm/adapter.py` — the only thing getting deleted

**What is getting deleted Saturday (today):**
`src/llm/adapter.py`, `src/llm/openrouter.py`, `src/llm/anthropic.py`

**What is being added Saturday (today):**
`src/agents/signal_agent.py` (~50 lines) — Strands `Agent(model=..., tools=[...], system_prompt=...)`

**What is completely unchanged by the pivot:**
Bronze/Silver/Gold pipeline, MCP servers (currently 3 of 7), `src/prompts/`, delivery code (built in Phase B), all tests, frontend schema contract.

**Smoke test before Phase B work:**
After the Saturday pivot, run `python run_demo.py` end-to-end before touching anything else. Confirm the Strands agent produces the same ranked digest and brief that the thin adapter produced on Friday. This is the gate to starting Phase B feature work.
