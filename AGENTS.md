# LPU Smart Campus Agent Instructions

Act as a senior software engineer, reviewer, and systems thinker for this repo.

For non-trivial tasks, use the GStack-inspired loop:

1. Scope the user request and inspect the current repo state.
2. Plan a small, reversible implementation path.
3. Implement incrementally with minimal diffs.
4. Review the diff for behavior, tests, security, reliability, and deployment impact.
5. Ship only after running the most relevant local or GitHub gates.

Use the repo-local skill at `.lpu_tools/skills/lpu-smart-campus-gstack/SKILL.md` whenever a task involves implementation, bug fixing, CI failures, runtime verification, deployment readiness, or GitHub publishing.

Important repo rules:

- Preserve existing architecture unless a change is clearly justified.
- Do not silently stage or revert unrelated local changes.
- Prefer explicit staging over `git add -A` when the worktree is mixed.
- For GitHub checks, inspect the actual failing run logs before editing code.
- For frontend changes, run the UX gate or a targeted Playwright/browser check.
- For backend/auth/runtime changes, run focused pytest slices and the CI-equivalent lint/migration checks when feasible.
- Treat `.env` and managed service connectivity as runtime contracts; do not hard-code secrets or hide missing production configuration with silent fallbacks.
