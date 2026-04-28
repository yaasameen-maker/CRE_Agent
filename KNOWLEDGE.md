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

---

## MCP Servers

**Every MCP tool must cache to Bronze before returning.**
The pattern is: check Bronze cache first → if hit, return cached row → if miss, call the external API, write to Bronze, return result. Never call ATTOM, RentCast, or any other rate-limited API without checking the cache first.

**HUD is the 7th data source — easy to miss.**
Early PRD drafts listed 6 sources (FRED, ATTOM, RentCast, BLS, Census, FHFA). Yaasameen's final PRD added HUD (huduser.gov) for office/residential vacancy trends. There should be 7 MCP servers total, not 6.

**The `@tool` decorator auto-generates the JSON schema Claude sees.**
Write clean type hints and a clear one-line docstring on every tool function — that becomes the contract Claude uses to decide when and how to call the tool. A vague docstring = Claude calling the tool incorrectly.

---

## SQLite

**Database lives at `data/cre_signal.db`.**
The `data/` directory is gitignored. Do not commit the database. Schema migrations live in `data/migrations/` (tracked) and are applied on startup.

---

## Strands Migration (Phase A → Phase B, Saturday 2026-05-02)

**Strands doesn't speak OpenRouter — that's why Phase A uses a thin adapter.**
Strands has native Anthropic API support but requires LiteLLM as a bridge for OpenRouter. Using a bridge adds complexity and makes the Saturday swap harder. The thin adapter is the right call for Days 1–4.

**The refactor is small by design.**
Everything in Phase A is structured to make the Saturday swap a one-day job:
- `src/prompts/scoring.py` — standalone string constants, Strands reads them unchanged
- `src/mcp/*.py` — `@tool` decorated functions in exactly the format Strands expects
- `src/llm/adapter.py` — the only thing getting deleted

**What gets deleted Saturday:**
`src/llm/adapter.py`, `src/llm/openrouter.py`, `src/llm/anthropic.py`

**What gets added Saturday:**
`src/agents/signal_agent.py` (~50 lines) — Strands `Agent(model=..., tools=[...], system_prompt=...)`

**What is completely unchanged:**
Bronze/Silver/Gold pipeline, all 7 MCP servers, `src/prompts/`, delivery code, all tests, frontend schema contract.

**Smoke test before starting Phase B work.**
After the Saturday pivot, run `python run_demo.py` end-to-end before touching anything else. Confirm the Strands agent produces the same ranked digest and brief that the thin adapter produced on Friday.
