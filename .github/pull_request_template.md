## What this PR does

<!-- One sentence. What changed and why. -->

## Branch type

- [ ] `feat/*` — new feature
- [ ] `fix/*` — bug fix
- [ ] `doc/*` — documentation update
- [ ] `hotfix/*` — immediate production issue

## Pre-merge checklist

**Local (must be done before pushing):**
- [ ] Tests written for all new code
- [ ] `pytest tests/unit/` passes locally
- [ ] `pytest tests/integration/` passes locally (if applicable)
- [ ] `pre-commit run --all-files` passes with no errors

**This PR:**
- [ ] All CI checks are green (Lint/Format/Type, Unit Tests, Integration Tests)
- [ ] Security checks are green (Bandit, Secrets Detection, pip-audit)
- [ ] Branch name follows convention (`feat/`, `fix/`, `doc/`, `hotfix/`)
- [ ] Commit messages are descriptive

## Testing notes

<!-- What did you test manually? What edge cases did you verify? -->

## Breaking changes

<!-- Does this change the shared JSON schema or any interface Yaasameen's frontend depends on? -->
