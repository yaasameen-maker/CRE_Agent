# Contributing to CRE Signal Agent

## Development Workflow

Every change follows this exact sequence — no exceptions:

```
1. Write code
2. Write tests for that code
3. Run unit tests locally — must pass
4. Run integration tests locally (if applicable) — must pass
5. Run pre-commit hooks — must pass
6. Commit to a feature branch
7. Push → CI runs automatically
8. Fix any CI failures
9. Open PR → code review
10. Merge to main only after: all checks green + 1 approval
```

## Branch Naming

Branches **must** follow this pattern or the branch-check CI job will fail:

| Type | Pattern | When to use |
|------|---------|-------------|
| New feature | `feat/<short-description>` | Any new capability |
| Bug fix | `fix/<short-description>` | Fixing broken behavior |
| Documentation | `doc/<short-description>` | Docs, comments, README |
| Urgent patch | `hotfix/<short-description>` | Production-breaking issue |

**Examples:**
```
feat/llm-abstraction-layer
feat/rentcast-data-ingestor
fix/zip-normalization-null-handling
doc/api-schema-contract
hotfix/scheduler-not-firing
```

## Commit Messages

Use this format: `<type>: <short description>`

| Type | Use for |
|------|---------|
| `feat:` | New functionality |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `chore:` | Tooling, config, CI changes |
| `test:` | Adding or fixing tests |
| `refactor:` | Code restructure, no behavior change |

**Examples:**
```
feat: add OpenRouter LLM adapter with cache_control support
fix: handle missing RentCast vacancy data gracefully
test: add unit tests for ZIP normalization logic
chore: update pre-commit hooks to ruff 0.4.4
```

## Pre-Commit Hooks

Hooks run automatically on `git commit` and `git push`. To run them manually:

```bash
# Run all hooks against all files
pre-commit run --all-files

# Run a specific hook
pre-commit run ruff --all-files
pre-commit run pytest-unit --all-files
```

If a hook fails, fix the issue and re-stage before committing:
```bash
git add <fixed files>
git commit -m "your message"
```

## Test Structure

```
tests/
  unit/          # Fast. No API keys. Runs on every commit via pre-commit.
  integration/   # Needs API keys. Runs on pre-push and in CI.
  e2e/           # Full pipeline. CI only.
```

**Rule:** Every new function in `src/` needs a corresponding test in `tests/unit/`. No exceptions.

## Security Rules

- Never hardcode API keys, passwords, or tokens — use environment variables
- Never commit `.env` files — they are gitignored
- If detect-secrets flags a false positive, update the baseline: `detect-secrets scan > .secrets.baseline`
- If Bandit flags a false positive, add a `# nosec B<code>` comment with a justification

## Environment Setup

```bash
# Clone and set up
git clone <repo>
cd cre-signal-agent
python -m venv .venv
source .venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
pre-commit install --hook-type pre-push

# Copy env template and fill in keys
cp .env.example .env
```
