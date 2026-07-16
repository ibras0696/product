# AI Engineering Harness

Rules are intentionally stored only in the platform-owned directories. Codex reads `.codex/config.toml`; Claude Code reads `.claude/CLAUDE.md`. They contain equivalent standalone contracts—neither imports the other and there are no scattered `AGENTS.md` or `CLAUDE.md` files.

| Capability | Codex | Claude Code |
| --- | --- | --- |
| Strict repository rules | `.codex/config.toml` | `.claude/CLAUDE.md` |
| Custom subagents | `.codex/agents/*.toml` | `.claude/agents/*.md` |
| Canonical skills | `.codex/skills/*` | `.claude/skills/*` symlinks |

Both contracts enforce DDD-lite module boundaries, strict routes/service/domain/repository/models responsibilities, meaningful scenario tests, KISS/YAGNI/DRY/SOLID, mobile-first frontend rules, production infrastructure constraints, file limits, and final quality gates. Every custom subagent is explicitly required to load its platform contract and applicable skills; the parent agent remains responsible for integration and validation.

## Product-to-delivery workflow

Do not load every role for every request. Use the smallest relevant set and pass a reviewed artifact to the next role:

1. `project-product-manager`: frame the problem, audience, evidence, value, MVP, priority, and measurable outcome.
2. `project-business-analyst`: turn the approved direction into actors, rules, scope, requirements, edge cases, acceptance criteria, and outcome-to-test traceability.
3. `ui-ux-pro-max`: create or update the shared mobile-first design system and interaction model after requirements are stable. Combine it with the existing design, React, and accessibility skills during implementation.
4. `team-agent-orchestration`: split approved delivery work into non-overlapping owned tasks with evidence and merge gates. Use it only when work is genuinely parallel.
5. Run the relevant engineering skills and finish with `project-quality-gate`.

Example prompts:

```text
Use $project-product-manager in best-guess mode. Turn this hackathon case into a one-page product brief and label every assumption.

Use $project-business-analyst. Convert the approved brief into MVP scope, business rules, edge cases, Given/When/Then acceptance criteria, and a traceability table.

Use $ui-ux-pro-max. Build one mobile-first design system from the approved requirements, then specify desktop adaptations and accessibility states.

Use $team-agent-orchestration. Split the approved implementation into bounded backend, frontend, test, and infrastructure work items with validation and merge gates.
```

The canonical skill files live only in `.codex/skills/`. Claude Code receives the same files through `.claude/skills/` symlinks; `.agents/skills` is intentionally not used.

Run the complete fail-closed validation with:

```bash
./scripts/quality_gate.sh
```

It checks harness wiring, code-size and complexity limits, backend formatting/lint/types/import architecture/tests, frontend formatting/lint/types/module boundaries/tests/build, all Compose variants, Alembic drift, live service health, desktop/mobile E2E, and accessibility.
