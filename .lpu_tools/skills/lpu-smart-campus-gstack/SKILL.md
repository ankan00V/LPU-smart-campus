---
name: lpu-smart-campus-gstack
description: Use for LPU Smart Campus implementation, bug fixing, CI triage, runtime verification, deployment readiness, and GitHub publishing. Applies the repo's GStack-style workflow with gates for the FastAPI, Mongo/Postgres/Redis, and static frontend stack.
---

# LPU Smart Campus GStack Workflow

Use this skill for substantial work in this repository. Keep it lean: inspect first, edit narrowly, verify with the same surfaces GitHub and production use.

## Core Loop

1. Scope
   - Read the user's exact failure or desired behavior.
   - Check `git status --short --branch` before touching files.
   - Locate the relevant code with `rg` and read the surrounding implementation.
   - If GitHub is mentioned, inspect `gh run list`, `gh run view`, or PR checks before guessing.

2. Plan
   - Prefer the smallest change that fixes the observed root cause.
   - Separate unrelated local changes from the intended diff.
   - For frontend work, identify the DOM, CSS, and Playwright surfaces affected.
   - For backend work, identify the router/service/schema/test contract affected.

3. Implement
   - Use existing app patterns and helpers before adding abstractions.
   - Keep changes scoped to the failing workflow.
   - Avoid broad fallbacks that mask production misconfiguration.
   - Do not edit `.env` unless the user explicitly asks for environment changes.

4. Review
   - Run `git diff --check`.
   - Review changed files for accidental debug logs, secrets, broad selectors, and cache/version mismatches.
   - Do not stage generated reports, local databases, caches, or ad-hoc scripts unless explicitly requested.

5. Ship
   - Stage explicit files only.
   - Commit with a terse, accurate message.
   - Push the active branch and watch the resulting GitHub Actions run when CI confidence matters.

## Local Verification Matrix

Run the narrowest useful set first, then broaden when risk justifies it.

- Migration gate:
  `APP_RUNTIME_STRICT=false APP_MANAGED_SERVICES_REQUIRED=false SQLALCHEMY_DATABASE_URL= PYTHONPATH=. .venv/bin/python scripts/check_migrations.py`
- Python lint:
  `PYTHONPATH=. .venv/bin/python -m ruff check app tests scripts`
- Focused backend tests:
  `PYTHONPATH=. .venv/bin/python -m pytest -q <test-path-or-node>`
- CI-style tracked tests, when local env allows:
  `git ls-files 'tests/test_*.py' 'scripts/test_*.py' | xargs env PYTHONPATH=. .venv/bin/python -m pytest -q`
- UX gate:
  `npm run ux:gates`
- Security gate:
  `PYTHONPATH=. .venv/bin/python -m bandit -q -r app scripts -x tests -lll`
  and the workflow's `pip-audit` command when dependency changes are involved.

## Runtime Notes

- This app uses FastAPI plus SQLAlchemy/Postgres, MongoDB mirrors, Redis/rate-limit/realtime paths, and a static `web/` frontend.
- Local `.env` may enable managed-runtime checks that GitHub CI does not enable. If a local gate fails from leaked managed env, rerun with explicit CI-style overrides and report that distinction.
- Redis is expected to have failover behavior. Do not replace that with a silent no-op unless the user explicitly asks for dev-only behavior.
- Frontend cache query strings in `web/index.html` matter for browser-visible changes.

## GitHub Checks

Use the actual GitHub run as the final source of truth when the user asks about failing checks:

```bash
gh run list --limit 10
gh run view <run-id> --json status,conclusion,url,headBranch,headSha,jobs
gh run watch <run-id> --exit-status
```

If a run fails, inspect the failing job log before editing. Fix the cause, push, and watch the replacement run.
