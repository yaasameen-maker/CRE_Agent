# CRE Signal Agent — Agent Conventions

AI-powered commercial real estate distress signal scorer. Ingests public data (FRED, ATTOM, BLS, Census, FHFA, RentCast, HUD) via MCP servers, scores signals, and delivers a daily ranked digest before 8am.

## Ownership

| Directory | Owner | Rule |
|-----------|-------|------|
| `src/` | Beatrice | Do not modify. Backend only. |
| `frontend/` | Yaasameen | Do not modify. Frontend only. |
| `.github/` | Both | Changes require approval from both owners. |
| `docs/schema/` | Both | Changes require agreement from both owners before modifying. |
| `data/migrations/` | Beatrice | Schema migrations. Do not modify. |

If you are working in `frontend/`, do not read, edit, or generate files under `src/`, and vice versa.

## Branch Naming

All branches must use one of these prefixes. PRs from branches that do not match will be rejected by CI:

- `feat/*` — new features
- `fix/*` — bug fixes
- `doc/*` — documentation only
- `hotfix/*` — emergency fixes

Examples: `feat/signal-scoring`, `fix/rentcast-null-handling`, `doc/update-schema`

## Commit Message Format

```
feat: short description
fix: short description
docs: short description
chore: short description
test: short description
refactor: short description
```

One line. Imperative mood. No trailing period. Keep it under 72 characters.

## Tests

Write tests before committing code. Run them locally before pushing:

- Backend tests: `pytest tests/unit/` and `pytest tests/integration/`
- Frontend tests: whatever test runner is configured in `frontend/`

Do not push code that makes tests fail.

## Shared JSON Schema

The contract between backend and frontend lives in `docs/schema/`:

```
docs/schema/
  signal_digest.json      # Array of scored signals (Gold layer output)
  opportunity_brief.json  # Per-asset brief structure
  action_alert.json       # Model / Monitor / Ignore classification
```

The frontend reads the Gold layer JSON. The backend writes it. Do not change any schema file without explicit agreement from both Beatrice and Yaasameen. Breaking the schema breaks the integration.

## Secrets

- Never hardcode API keys, tokens, passwords, or credentials in any file.
- Use environment variables. Load from `.env` using your project's env loading mechanism.
- `.env` is gitignored. Never commit it, stage it, or reference its values in code.
- If you accidentally expose a secret in a commit, notify the team immediately.

## Git Workflow

- Never push directly to `main`. Always use a feature branch.
- Open a pull request and wait for CI to pass before merging.
- Do not merge your own PR without review if another team member is available.
- Do not run `git push --force` on shared branches.
- Squash or rebase to keep history clean before merging.

## Pre-Push Checklist

Before pushing any branch:

1. Tests pass locally
2. No hardcoded secrets
3. Branch name follows the naming rule above
4. Commit messages follow the format above
5. You have not modified files outside your ownership area
