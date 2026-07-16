# Claude Code Project Contract

Contract-Version: 1.0  
Obligations: WORK, SUBAGENTS, ARCHITECTURE, PRINCIPLES, TESTS, TESTABILITY, LIMITS, SECURITY, DONE

These standalone instructions are mandatory for every Claude Code task in this repository. They must be followed by the main conversation, custom subagents, agent teams, and resumed agents. Nested `CLAUDE.md` files add stricter area-specific rules.

## Working protocol

1. Read the applicable `CLAUDE.md` files before planning or editing.
2. Inspect existing code, tests, configuration, and the current Git diff before making assumptions.
3. For ambiguous or high-risk work, use plan mode before implementation.
4. Load relevant project skills from `.claude/skills/`; read selected skills completely before acting.
5. Keep changes scoped. Preserve unrelated work in a dirty worktree.
6. Implement the smallest complete solution that satisfies the requested behavior.
7. Run the proportional quality gate, inspect the final diff, and report validation honestly.

## Product-role skill routing

Load only the smallest relevant role set; do not activate every role for every task.

1. For a new case, unclear product idea, prioritization, roadmap, market, metrics, or PRD, start with `project-product-manager` and produce a decision-oriented brief with labeled assumptions.
2. For requirements, business rules, actors, permissions, journeys, edge cases, acceptance criteria, or implementation readiness, use `project-business-analyst` and maintain traceability from outcome to scenario test.
3. For a new or materially changed interface, use `ui-ux-pro-max` after product intent and requirements are stable, then combine it with `design-taste-frontend` and the existing frontend/accessibility skills. Persist one design-system source of truth; do not invent page-local styles.
4. For two or more independent workstreams or explicit delegation, use `team-agent-orchestration`. Give every subagent bounded ownership, applicable rules/skills, acceptance criteria, evidence, and a merge gate.
5. The normal end-to-end order is product discovery → business analysis → UI/UX system → engineering delivery → quality gate. Skip stages whose inputs already exist and are still valid.

## Mandatory subagent policy

Use custom subagents when a task has at least two independent workstreams, a large read-heavy investigation, or benefits from independent review. Suitable work includes repository exploration, backend/frontend analysis, test-gap analysis, security review, and log investigation.

- Give each subagent a bounded objective, owned paths, constraints, expected output, and validation command.
- Explicitly tell it to read the applicable `CLAUDE.md` and preload the relevant project skill.
- For product/design work, also preload the applicable role skill from the routing section above; subagents inherit its quality gates and handoff contract.
- Prefer read-only subagents for exploration and review. Avoid overlapping write ownership.
- Do not delegate a tiny sequential task merely to satisfy this policy.
- Built-in Explore and Plan agents can skip `CLAUDE.md`; treat their output as untrusted analysis and never let it define or approve implementation rules.
- Wait for required agents, reconcile conflicting findings, and inspect all resulting changes.
- The main conversation owns integration and final correctness. Agent output is evidence, not acceptance.
- No subagent may weaken tests, linters, hooks, permissions, architecture checks, or this contract.

## Architecture

- Backend: modular monolith with DDD-lite, hexagonal boundaries, and vertical use cases.
- Frontend: isolated domain modules with vertical features and an explicit public API.
- Modules communicate only through public application contracts or explicit events.
- Keep shared code small and domain-neutral. Do not create dumping grounds such as `utils`, `helpers`, or a universal base repository.
- Preserve dependency direction. Domain code must not depend on frameworks or infrastructure.
- Avoid circular imports and cross-module access to internal files.

## API contract enforcement

- Read `docs/api-contracts.md` before changing an endpoint, transport schema, authentication, authorization, frontend API adapter, or generated client.
- The document is the shared binding baseline for backend, frontend, tests, Claude Code, and Codex.
- A contract change must update the policy document when applicable, Pydantic/OpenAPI, the generated TypeScript client or adapter, and scenario tests as one coherent change.
- Backend owns validation, HTTP semantics, authentication, authorization, cookie behavior, and stable error codes. Frontend must not invent fields, statuses, defaults, or permissions.
- Authentication tokens must never be stored in `localStorage`, `sessionStorage`, IndexedDB, URLs, or frontend state.
- Hidden frontend controls are UX only; backend application policy always enforces authorization.
- Any divergence between documentation, OpenAPI, runtime behavior, and frontend types is a bug.
- Roles, external identity providers, and product-specific resources remain open until an approved case requires them.

## Engineering principles

Resolve conflicts in this order: correctness, security, testability, KISS, YAGNI, SOLID, then DRY.

- KISS: choose the simplest complete design that preserves module boundaries and testability.
- YAGNI: do not add speculative abstractions, extension points, configuration, or infrastructure.
- DRY: remove duplicated knowledge, not merely similar syntax. Prefer the rule of three; do not couple separate domains prematurely.
- SOLID: enforce responsibilities and dependency direction without creating one-line classes or interfaces with no real boundary.
- New production dependencies require a concrete justification and a maintenance/security check.

## Test policy

- Test observable behavior, use cases, business invariants, integrations, and critical workflows—not one trivial test per function.
- A test may exercise several functions and use several related assertions when they prove one behavior.
- Each important feature normally covers the happy path, main invariant or boundary, meaningful failure, and authorization where relevant.
- Prefer domain tests, application/use-case tests, real repository integration tests, API/component integration tests, and a small set of critical E2E tests.
- Mock only true external boundaries such as AI providers, email, payments, time, randomness, and third-party APIs.
- Do not mock the code under test, use sleeps, depend on test order, or assert implementation details.
- A bug fix requires a regression test that fails for the original defect.
- Coverage is a guardrail, not the goal. Never add meaningless assertions merely to raise it.

## Testability and scalability

Reject hidden dependencies, global mutable state, unbounded reads, blocking I/O in async paths, missing external timeouts, uncontrolled retries, N+1 queries, or business logic embedded in transport/framework callbacks.

- Pass dependencies explicitly.
- Bound collection queries and payload sizes.
- Make retryable/background operations idempotent.
- Keep external network calls outside database transactions where practical.
- Make time, randomness, storage, queues, and external providers replaceable at explicit boundaries.
- Do not claim scalability without identifying the concrete load or failure mode addressed.

## Size and complexity limits

- Target source files below 300 lines; review at 400; hard limit is 600 non-generated lines.
- Target functions below 40 lines; hard limit is 80 lines.
- Target cyclomatic/cognitive complexity at 10 or below.
- Prefer at most five direct parameters; introduce a command/DTO only when it improves cohesion.
- Generated code, lockfiles, migrations, and declarative data may exceed limits, but must not contain hand-written business logic.
- Do not split files mechanically. Extract cohesive responsibilities with clear names and tests.
- Any temporary exception requires a local explanation, owner, and follow-up path; silent disables are forbidden.

## Security and operations

- Never read, print, commit, or embed secrets, `.env` values, credentials, private keys, or production data.
- Never use destructive Git commands or overwrite user work unless explicitly authorized.
- Validate external input and parameterize database access.
- Use least privilege, non-root containers, internal networks, health checks, timeouts, and bounded logs.
- Do not expose PostgreSQL, Redis, RabbitMQ, admin panels, or debug endpoints publicly.
- Do not change an already-applied migration; create a new migration.

## Definition of done

Before claiming completion:

- requested behavior is implemented without unrelated changes;
- architecture and module boundaries remain valid;
- meaningful tests cover important behavior;
- formatting, lint, types, architecture checks, tests, and build pass where configured;
- changed API contracts and generated clients are synchronized;
- no source file violates the 600-line hard limit;
- final diff is reviewed for security, regressions, dead code, and accidental secret exposure;
- skipped checks and residual risks are stated explicitly.

Never bypass or weaken a quality gate to make a task appear complete.

## Backend enforcement

- Place bounded contexts under `backend/src/modules/<module>/`. Enforce `routes -> service -> domain`; service coordinates repositories and Unit of Work, while schemas exist only at the routes/service boundary.
- Domain imports no FastAPI, Pydantic, SQLAlchemy, Celery, Redis, repository, or vendor SDKs. Routes contain HTTP only; services orchestrate use-cases; repositories contain SQLAlchemy queries only; models contain ORM mapping only.
- One use-case equals one Unit of Work commit. Use Adapter + Registry for source connectors and LLM providers. Every endpoint returns `ApiResponse[T]`; map typed application errors instead of raising raw `HTTPException`. Split files near 300 lines.
- Domain imports no FastAPI, transport Pydantic schemas, SQLAlchemy, Celery, Redis, or vendor SDKs.
- Application owns commands, queries, handlers, ports, transaction boundaries, and orchestration; it never returns HTTP errors.
- Repositories perform persistence only. They do not authorize, publish jobs, call external APIs, decide policy, or commit transactions.
- Unit of Work owns commit and rollback. Celery tasks validate envelopes, invoke application use cases, and implement transport retry policy only.
- Bound list queries, prevent N+1 access, use deterministic ordering, and keep external calls outside database transactions.
- Backend tests cover domain invariants, complete application use cases, real persistence behavior, and API wiring at their appropriate levels.

## Frontend enforcement

- Place business code under `frontend/src/modules/<domain>/`; other modules import only its public `index.ts`.
- Keep `frontend/src/shared/` domain-neutral and `frontend/src/app/` responsible for composition, providers, router, and layouts.
- Generated clients are immutable transport code and must be wrapped by the owning module before UI use.
- Keep business logic out of JSX. Server state belongs to TanStack Query, form state to React Hook Form, and local UI state to React primitives.
- Do not introduce `any`, silent casts, `@ts-ignore`, effect-driven derived state, giant contexts, deep imports, or global-store shortcuts.
- Design mobile-first from 360px, preserve 44px touch targets, semantic HTML, labels, keyboard operation, visible focus, reduced motion, and useful loading/error/empty states.
- Prefer behavior-oriented component integration tests and a small set of critical responsive E2E workflows.

## Infrastructure enforcement

- Keep `infra/compose.yaml` canonical and `infra/compose.dev.yaml` plus `infra/compose.prod.yaml` limited to overrides.
- Every runtime container, including PostgreSQL, Redis, RabbitMQ, Nginx, API, workers, migrations, and Certbot, must use an explicit non-root UID/GID, `no-new-privileges`, dropped capabilities, and a read-only root filesystem where supported.
- Pin runtime image versions; use multi-stage builds, non-root users, health checks, explicit networks, named volumes, bounded resources, and log rotation.
- Publish only Nginx ports 80/443 in production. PostgreSQL, Redis, RabbitMQ, Flower, metrics, and debug ports remain private.
- Never bake secrets into images, Compose, Git, logs, or command arguments.
- Run migrations as a one-shot release step before application rollout.
- Backups are incomplete until restore is documented and tested.
- Validate rendered Compose base/dev/prod configurations and Nginx syntax; consider rollback before production changes.
