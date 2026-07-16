---
name: project-quality-gate
description: Verify any implementation, refactor, bug fix, or review before completion in this repository. Use proactively before saying work is done. Enforces architecture, meaningful tests, strict types, file and function limits, KISS/YAGNI/DRY/SOLID, security, scalability, and honest reporting for backend, frontend, and infrastructure.
---

# Project Quality Gate

1. Read the active platform contract in `.codex/config.toml` or `.claude/CLAUDE.md`.
2. Inspect `git status` and the complete diff. Separate user changes from task changes.
3. Verify requested behavior and look for missing error, authorization, loading, empty, retry, and rollback paths.
4. Check architectural ownership and dependency direction. Reject deep cross-module imports, business logic in routers/components/tasks/repositories, and shared dumping grounds.
5. Check simplicity: remove speculation, unnecessary wrappers, premature DRY abstractions, dead code, and unused configuration.
6. Check test quality using `project-testing`; do not accept coverage-only or implementation-coupled tests.
7. Run `python3 scripts/check_file_sizes.py` and all configured format, lint, type, architecture, test, migration, build, E2E, and security checks proportional to the diff.
8. Review scalability hazards: unbounded reads, blocking async work, N+1 queries, missing timeouts, uncontrolled retries, non-idempotent jobs, giant renders, and duplicated server state.
9. Review secrets, input validation, permissions, public ports, image users, and dependency changes.
10. Report exact commands and outcomes. Never hide skipped checks or weaken a gate to pass.

For non-trivial changes, use independent read-only reviewer and test-gap subagents. The main agent must validate their findings against the actual diff.
