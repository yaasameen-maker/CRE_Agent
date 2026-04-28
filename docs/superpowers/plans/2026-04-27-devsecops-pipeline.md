# DevSecOps Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a full DevSecOps pipeline with pre-commit local enforcement, branch naming standards, CI validation, security scanning, and code review gates — so every standard is enforced automatically from day one.

**Architecture:** Three-layer enforcement: (1) local pre-commit hooks catch issues before any commit lands, (2) GitHub Actions CI validates on every branch push and PR, (3) branch protection rules require all checks to pass and a review before merging to main. Security runs at every layer, not just CI.

**Tech Stack:** pre-commit, ruff, mypy, bandit, detect-secrets, pytest, pytest-cov, pip-audit, GitHub Actions, gh CLI

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `.pre-commit-config.yaml` | Create | Local hook runner — ruff, mypy, bandit, detect-secrets, pytest unit |
| `.github/workflows/ci.yml` | Update | Lint + type check + test + coverage threshold |
| `.github/workflows/security.yml` | Update | Bandit SAST + pip-audit dependency audit (scheduled + PR) |
| `.github/workflows/branch-check.yml` | Create | Enforce branch naming convention on every PR |
| `.github/pull_request_template.md` | Create | PR checklist enforcing the full dev workflow |
| `.github/CODEOWNERS` | Create | Required reviewer assignments |
| `pyproject.toml` | Update | Add coverage config, detect-secrets baseline path |
| `requirements-dev.txt` | Update | Add pre-commit, pytest-cov, detect-secrets |
| `tests/unit/.gitkeep` | Create | Unit test directory |
| `tests/integration/.gitkeep` | Create | Integration test directory (CI only — needs API keys) |
| `tests/e2e/.gitkeep` | Create | E2E test directory (CI only — full stack) |
| `CONTRIBUTING.md` | Create | Developer workflow, branch naming, commit message standards |
| `.secrets.baseline` | Create | detect-secrets baseline (empty scan of clean repo) |

---

## Task 1: Test Directory Structure

**Files:**
- Create: `tests/unit/.gitkeep`
- Create: `tests/integration/.gitkeep`
- Create: `tests/e2e/.gitkeep`
- Create: `tests/__init__.py`
- Update: `pyproject.toml`

- [ ] **Step 1: Create the test directories**

```bash
mkdir -p tests/unit tests/integration tests/e2e
touch tests/__init__.py
touch tests/unit/.gitkeep
touch tests/integration/.gitkeep
touch tests/e2e/.gitkeep
```

- [ ] **Step 2: Add coverage config to pyproject.toml**

Open `pyproject.toml` and add this section after `[tool.pytest.ini_options]`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]

[tool.coverage.run]
source = ["src"]
omit = ["tests/*", ".venv/*"]

[tool.coverage.report]
fail_under = 80
show_missing = true
```

- [ ] **Step 3: Verify pytest can discover tests (no failures expected on empty dirs)**

```bash
pytest tests/ -v
```

Expected output: `no tests ran` — this is correct for empty directories.

- [ ] **Step 4: Commit**

```bash
git add tests/ pyproject.toml
git commit -m "chore: scaffold test directory structure and coverage config"
```

---

## Task 2: Pre-Commit Hook Framework

**Files:**
- Create: `.pre-commit-config.yaml`
- Create: `.secrets.baseline`
- Update: `requirements-dev.txt`

Pre-commit runs locally before every `git commit`. The hook order matters: fast checks first (ruff), then security (detect-secrets, bandit), then slow checks (mypy, pytest). This gives the fastest feedback loop.

- [ ] **Step 1: Add pre-commit and detect-secrets to requirements-dev.txt**

Replace the contents of `requirements-dev.txt` with:

```text
# Code quality
ruff>=0.4.0
mypy>=1.10.0

# Security
bandit[toml]>=1.7.0
pip-audit>=2.7.0
detect-secrets>=1.5.0

# Testing
pytest>=8.0.0
pytest-cov>=5.0.0

# Local enforcement
pre-commit>=3.7.0
```

- [ ] **Step 2: Install dev dependencies**

```bash
pip install -r requirements-dev.txt
```

- [ ] **Step 3: Generate the detect-secrets baseline on the clean repo**

This scans the current codebase and records any false positives so future scans only flag *new* secrets.

```bash
detect-secrets scan > .secrets.baseline
```

- [ ] **Step 4: Create .pre-commit-config.yaml**

```yaml
# .pre-commit-config.yaml
repos:
  # Ruff: lint (with autofix) + format
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.4
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  # detect-secrets: block accidental credential commits
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: [--baseline, .secrets.baseline]
        exclude: .secrets.baseline

  # Bandit: Python security static analysis
  - repo: local
    hooks:
      - id: bandit
        name: bandit — security scan
        entry: bandit -r src/ -c pyproject.toml
        language: system
        pass_filenames: false
        stages: [commit]

  # Mypy: type checking
  - repo: local
    hooks:
      - id: mypy
        name: mypy — type check
        entry: mypy src/
        language: system
        pass_filenames: false
        stages: [commit]

  # Pytest: unit tests only (fast, no API keys needed)
  - repo: local
    hooks:
      - id: pytest-unit
        name: pytest — unit tests
        entry: pytest tests/unit/ -v --tb=short -q
        language: system
        pass_filenames: false
        stages: [commit]

  # Pytest: integration tests on push only (may need env vars)
  - repo: local
    hooks:
      - id: pytest-integration
        name: pytest — integration tests
        entry: pytest tests/integration/ -v --tb=short -q
        language: system
        pass_filenames: false
        stages: [push]
```

- [ ] **Step 5: Install pre-commit into the local git repo**

```bash
pre-commit install          # installs commit-stage hooks
pre-commit install --hook-type pre-push  # installs push-stage hooks
```

Expected output:
```
pre-commit installed at .git/hooks/pre-commit
pre-commit installed at .git/hooks/pre-push
```

- [ ] **Step 6: Run all hooks against the full repo to verify no baseline failures**

```bash
pre-commit run --all-files
```

Expected: all hooks pass (ruff may autofix a few style issues, re-stage those). If bandit or mypy fail, there's no `src/` directory yet — that's expected and will resolve once backend code exists.

- [ ] **Step 7: Commit**

```bash
git add .pre-commit-config.yaml .secrets.baseline requirements-dev.txt
git commit -m "chore: add pre-commit hooks for local DevSecOps enforcement"
```

---

## Task 3: Branch Naming Enforcement (GitHub Actions)

**Files:**
- Create: `.github/workflows/branch-check.yml`

This workflow runs on every PR to main and fails if the branch name doesn't match `feat/*`, `fix/*`, `doc/*`, or `hotfix/*`. The branch name is passed via `env:` (never interpolated directly into `run:` — injection-safe pattern).

- [ ] **Step 1: Create the branch-check workflow**

```bash
cat > .github/workflows/branch-check.yml << 'EOF'
name: Branch Name

on:
  pull_request:
    branches:
      - main

jobs:
  check-branch-name:
    name: Validate Branch Name
    runs-on: ubuntu-latest

    steps:
      - name: Check branch naming convention
        env:
          BRANCH_NAME: ${{ github.head_ref }}
        run: |
          echo "Branch: $BRANCH_NAME"
          if ! echo "$BRANCH_NAME" | grep -qE '^(feat|fix|doc|hotfix)/.+'; then
            echo ""
            echo "ERROR: Branch name '$BRANCH_NAME' does not follow naming convention."
            echo ""
            echo "Required pattern:  <type>/<description>"
            echo "Allowed types:     feat | fix | doc | hotfix"
            echo ""
            echo "Examples:"
            echo "  feat/llm-abstraction-layer"
            echo "  fix/rentcast-null-handling"
            echo "  doc/api-schema-contract"
            echo "  hotfix/scheduler-crash"
            exit 1
          fi
          echo "Branch name is valid."
EOF
```

- [ ] **Step 2: Verify the file was written correctly**

```bash
cat .github/workflows/branch-check.yml
```

Confirm the `env:` block wraps `github.head_ref` and the `run:` block uses `$BRANCH_NAME` (the env var), not `${{ github.head_ref }}` directly.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/branch-check.yml
git commit -m "chore: enforce branch naming convention via GitHub Actions"
```

---

## Task 4: Updated CI Workflow (Coverage + Integration Tests)

**Files:**
- Update: `.github/workflows/ci.yml`

Replace the existing `ci.yml` with a version that adds: coverage threshold enforcement (80%), a separate integration test job (skipped if no secrets available), and explicit job naming that matches what branch protection will reference.

- [ ] **Step 1: Rewrite ci.yml**

```bash
cat > .github/workflows/ci.yml << 'EOF'
name: CI

on:
  push:
    branches-ignore:
      - main
  pull_request:
    branches:
      - main

jobs:
  validate:
    name: Lint, Format & Type Check
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Ruff — lint
        run: ruff check .

      - name: Ruff — format check
        run: ruff format --check .

      - name: Mypy — type check
        run: mypy src/

  unit-tests:
    name: Unit Tests
    runs-on: ubuntu-latest
    needs: validate

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run unit tests with coverage
        run: pytest tests/unit/ -v --tb=short --cov=src --cov-report=term-missing --cov-fail-under=80
        env:
          LLM_PROVIDER: openrouter

  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    needs: unit-tests
    # Only run when secrets are available (PRs from forks won't have them — that's intentional)
    if: ${{ github.event_name != 'pull_request' || github.event.pull_request.head.repo.full_name == github.repository }}

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run integration tests
        run: pytest tests/integration/ -v --tb=short
        env:
          LLM_PROVIDER: openrouter
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
EOF
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "chore: add coverage threshold and integration test job to CI"
```

---

## Task 5: Security Workflow (Updated)

**Files:**
- Update: `.github/workflows/security.yml`

Add a detect-secrets scan job to catch any secrets that slipped past the pre-commit hook (e.g., if someone bypassed it with `--no-verify`).

- [ ] **Step 1: Rewrite security.yml**

```bash
cat > .github/workflows/security.yml << 'EOF'
name: Security

on:
  pull_request:
    branches:
      - main
  schedule:
    - cron: "0 9 * * 1"

jobs:
  sast:
    name: Static Analysis (Bandit)
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Install Bandit
        run: pip install bandit[toml]

      - name: Run Bandit
        run: bandit -r src/ -c pyproject.toml

  secrets-scan:
    name: Secrets Detection
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install detect-secrets
        run: pip install detect-secrets

      - name: Scan for secrets
        run: detect-secrets scan --baseline .secrets.baseline

  dependency-audit:
    name: Dependency Vulnerabilities (pip-audit)
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Install pip-audit
        run: pip install pip-audit

      - name: Audit dependencies
        run: pip-audit -r requirements.txt
EOF
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/security.yml
git commit -m "chore: add secrets detection job to security workflow"
```

---

## Task 6: PR Template and CODEOWNERS

**Files:**
- Create: `.github/pull_request_template.md`
- Create: `.github/CODEOWNERS`

- [ ] **Step 1: Create the PR template**

```bash
mkdir -p .github
cat > .github/pull_request_template.md << 'EOF'
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
EOF
```

- [ ] **Step 2: Create CODEOWNERS**

Replace `beatrice` and `yaasameen` with your actual GitHub usernames.

```bash
cat > .github/CODEOWNERS << 'EOF'
# All files require review from at least one owner
* @beatrice @yaasameen

# Backend — Beatrice reviews all src/ changes
src/ @beatrice

# Frontend — Yaasameen reviews all frontend/ changes (placeholder for when it exists)
# frontend/ @yaasameen

# CI/CD and security config — both must review
.github/ @beatrice @yaasameen
pyproject.toml @beatrice @yaasameen
EOF
```

- [ ] **Step 3: Commit**

```bash
git add .github/pull_request_template.md .github/CODEOWNERS
git commit -m "chore: add PR template and CODEOWNERS for review enforcement"
```

---

## Task 7: CONTRIBUTING.md — Developer Workflow Documentation

**Files:**
- Create: `CONTRIBUTING.md`

- [ ] **Step 1: Create CONTRIBUTING.md**

```bash
cat > CONTRIBUTING.md << 'EOF'
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
EOF
```

- [ ] **Step 2: Commit**

```bash
git add CONTRIBUTING.md
git commit -m "docs: add CONTRIBUTING.md with full DevSecOps workflow"
```

---

## Task 8: Branch Protection Rules (GitHub — run after first push)

This task requires the repo to exist on GitHub. Run these commands once after the initial push.

- [ ] **Step 1: Push the repo to GitHub**

```bash
git remote add origin https://github.com/YOUR_ORG/cre-signal-agent.git
git push -u origin main
```

- [ ] **Step 2: Apply branch protection via gh CLI**

Replace `YOUR_ORG/cre-signal-agent` with your actual repo path.

```bash
gh api repos/YOUR_ORG/cre-signal-agent/branches/main/protection \
  --method PUT \
  --header "Accept: application/vnd.github+json" \
  --field enforce_admins=true \
  --field restrictions=null \
  --field 'required_status_checks={"strict":true,"contexts":["Lint, Format & Type Check","Unit Tests","Integration Tests","Validate Branch Name","Static Analysis (Bandit)","Secrets Detection","Dependency Vulnerabilities (pip-audit)"]}' \
  --field 'required_pull_request_reviews={"required_approving_review_count":1,"dismiss_stale_reviews":true}'
```

- [ ] **Step 3: Verify branch protection is active**

```bash
gh api repos/YOUR_ORG/cre-signal-agent/branches/main/protection \
  --jq '.required_status_checks.contexts'
```

Expected output — all 7 check names listed:
```json
[
  "Lint, Format & Type Check",
  "Unit Tests",
  "Integration Tests",
  "Validate Branch Name",
  "Static Analysis (Bandit)",
  "Secrets Detection",
  "Dependency Vulnerabilities (pip-audit)"
]
```

- [ ] **Step 4: Test by attempting a direct push to main (should be rejected)**

```bash
echo "test" >> README.md
git add README.md
git commit -m "test: verify branch protection blocks direct push"
git push origin main
```

Expected: `remote: error: GH006: Protected branch update failed`

---

## Self-Review Against Spec

**Spec requirements vs. plan coverage:**

| Requirement | Task |
|------------|------|
| Tests written before code is pushed | Task 2 (pre-commit pytest-unit hook) |
| Unit/integration/E2E local testing | Tasks 1, 2 (directory structure + pre-push integration hook) |
| Code committed to branch, not main | Task 3 (branch-check workflow) + Task 8 (branch protection) |
| CI testing on branch | Task 4 (ci.yml) |
| Security as architectural consideration | Tasks 2, 5 (bandit + detect-secrets at commit + CI) |
| Code reviewed before main | Task 6 (CODEOWNERS + PR template) + Task 8 (required reviews) |
| Branch naming: feat/*, fix/*, doc/*, hotfix/* | Task 3 |
| Standards survive beyond MVP | Task 7 (CONTRIBUTING.md documents everything) |

**No placeholders found.** All steps contain exact commands, exact file contents, exact expected outputs.
