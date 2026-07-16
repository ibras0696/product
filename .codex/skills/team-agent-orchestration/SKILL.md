---
name: team-agent-orchestration
description: Coordinate Claude Code or Codex subagents as an engineering team with bounded work items, explicit ownership, non-overlapping file scopes, shared project rules, evidence, reviews, handoffs, and merge gates. Use when work has two or more independent streams, needs specialist backend/frontend/infra/test review, or the user requests delegation, parallel agents, a team lead, or agent orchestration.
---

# Team Agent Orchestration

Run agents as accountable teammates, not an unstructured fan-out. This project’s Claude/Codex contract and applicable project skills override this workflow.

## Decide whether to delegate

Use subagents for independent workstreams, large read-heavy investigations, or an independent specialist review. Keep tiny sequential work in the main agent. Never split work merely to appear parallel.

## Shape each work item before starting it

Define:

- objective and expected artifact;
- one owner;
- owned files or read-only scope;
- forbidden areas and dependencies;
- applicable Claude/Codex rules and required project skills;
- acceptance criteria;
- exact validation command or evidence;
- handoff format and merge gate.

Do not start two writing agents on overlapping files. If overlap is unavoidable, appoint one integrator and make the other agents read-only advisers.

## Execution flow

1. **Shape.** Convert the goal into the smallest independent work items. Keep one integration item with the main agent.
2. **Assign.** Give each agent enough context to act, but not unrelated history or the expected answer. Require it to read the applicable local rules and skills.
3. **Track.** Use only the states `ready`, `running`, `review`, `blocked`, and `done`. Create a persistent board only when work spans sessions or many agents; otherwise keep state in the active plan.
4. **Collect evidence.** Require changed paths, tests or commands, findings, risks, and unresolved questions. “Implemented” without evidence is not a handoff.
5. **Review.** Check acceptance criteria, diff, architecture, security, and tests. Reviewer output is evidence, never automatic approval.
6. **Integrate.** The main agent resolves conflicts, reruns the relevant quality gate, inspects the combined result, and owns the final claim.

## Mandatory controls

- Propagate strict architecture, KISS, YAGNI, SOLID, DRY, tests, file limits, security, and non-root infrastructure rules to every agent.
- Prefer read-only specialist agents for exploration, architecture, test-gap, and security review.
- Never let an agent weaken tests, linters, permissions, hooks, or CI to pass a gate.
- Preserve unrelated user work and never use destructive Git cleanup.
- Stop fan-out when work becomes sequential or shared context dominates the task.
- Escalate blockers with the missing decision, owner, and safest next action.

## Handoff contract

Every writing agent returns:

```text
Outcome:
Owned paths changed:
Acceptance criteria satisfied:
Validation and result:
Risks or skipped checks:
Next integration action:
```

Every reviewer returns findings ordered by severity, with concrete file evidence and a clear pass/fail recommendation.

## Failure modes

- **Agent soup:** many agents, no owners or merge gates.
- **Overlapping writes:** parallel edits to the same boundary.
- **Invisible work:** useful conclusions exist only in chat with no handoff.
- **Board theater:** status tracking without acceptance criteria.
- **Premature approval:** trusting a subagent’s success claim without integration checks.
- **Process excess:** orchestration costs more than doing the task directly.

Finish with work items completed, evidence, integration status, blockers with owners, and the remaining quality gate.

Workflow adapted and hardened for this repository from the public `affaan-m/ECC` team-agent-orchestration skill.
