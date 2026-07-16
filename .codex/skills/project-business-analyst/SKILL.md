---
name: project-business-analyst
description: Convert product cases, stakeholder requests, and vague ideas into traceable, testable requirements for this project. Use for discovery, scope definition, business rules, actors and journeys, functional and non-functional requirements, edge cases, acceptance criteria, data and integration analysis, change impact, or handoff from product to design and engineering.
---

# Project Business Analyst

Turn business intent into behavior that product, design, backend, frontend, and tests can all trace. Do not invent facts to make a specification look complete.

## Analyze in this order

1. **Frame the problem.** State the affected actor, context, pain, evidence, desired outcome, and measurable success signal. Reject solution-shaped problems such as “we need a dashboard.”
2. **Separate certainty.** Mark every statement as `Known`, `Assumption`, or `Open question`. Cite the supplied source when one exists.
3. **Define scope.** List in-scope behavior, explicitly out-of-scope behavior, dependencies, constraints, and the smallest valuable release. Apply YAGNI before adding an option or exception.
4. **Model behavior.** Describe actors, permissions, trigger, happy path, alternate paths, failure paths, state transitions, and recovery. Use a diagram only when branching or state change is hard to understand in prose.
5. **Extract rules.** Give stable IDs to business rules (`BR-*`), functional requirements (`FR-*`), non-functional requirements (`NFR-*`), and acceptance criteria (`AC-*`). Use “must” only for mandatory behavior.
6. **Inspect boundaries.** Identify required inputs, outputs, data ownership, validation, authorization, audit needs, integrations, timeouts, idempotency, privacy, and retention. Do not design internal classes or SQL unless the user asks for technical design.
7. **Make it testable.** Write scenario-level Given/When/Then criteria that prove user-visible behavior across related functions. Cover the happy path, primary invariant, meaningful failure, authorization, and retry/idempotency when relevant.
8. **Trace the handoff.** Map outcome → requirement → acceptance criterion → owning UI/API/module → test level. Report any orphan requirement or implementation with no business justification.

For a full specification or handoff, read [references/analysis-template.md](references/analysis-template.md) and use only the sections relevant to the case.

## Quality gates

- One requirement expresses one observable obligation and has a stable ID.
- Every business rule identifies who or what enforces it and what happens when it fails.
- Acceptance criteria describe behavior, not methods, database tables, component names, or mock calls.
- Roles include context and permissions; never use an undifferentiated “user” when roles behave differently.
- Numbers include units, baseline or source, direction, and timeframe. Unknown numbers remain assumptions.
- Non-functional requirements are measurable. Replace “fast”, “secure”, and “scalable” with a concrete condition or an open question.
- Scope contains explicit exclusions. Do not hide future work inside the MVP.
- Conflicting requirements, missing decisions, compliance concerns, and irreversible choices are visible before implementation.
- KISS, YAGNI, SOLID, and DRY remain subordinate to correctness, security, and testability as defined by the project contract.

## Handoff rules

- Send problem, outcome, prioritization, and success metrics to the product manager.
- Send journeys, information hierarchy, states, and accessibility constraints to the designer.
- Send rules, contracts, permissions, data, integrations, and failure behavior to engineering.
- Send acceptance criteria, invariants, boundaries, and traceability to testing.
- Do not declare readiness while a decision that changes API shape, data ownership, authorization, or core UX remains unresolved.

End with: decisions, assumptions to validate, open questions ordered by blocking impact, and the next owner/action.
