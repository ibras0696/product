---
name: project-backend-ddd
description: Implement or refactor FastAPI backend functionality in this repository using bounded contexts, DDD-lite, hexagonal boundaries, strict service/repository separation, Alembic, Celery, Redis, RabbitMQ, or PostgreSQL. Use for every backend feature, endpoint, domain model, repository, migration, integration, or background task.
---

# Project Backend DDD

1. Read the active platform contract in `.codex/config.toml` or `.claude/CLAUDE.md`.
2. Identify the owning bounded context before editing. Do not create a cross-cutting module to avoid choosing ownership.
3. State the use case, invariant, inputs, outputs, failure modes, transaction boundary, and external ports.
4. Search for existing public contracts and patterns. Preserve dependency direction.
5. Implement from inside out when business behavior is non-trivial:
   - domain entity/value object/event and invariant;
   - application command/query and handler;
   - repository/port protocol;
   - infrastructure implementation and mapper;
   - thin FastAPI or Celery adapter.
6. For CRUD with no real invariant, keep the slice small; do not manufacture entities, factories, and interfaces without a boundary.
7. Keep repositories persistence-only and Unit of Work responsible for commit/rollback.
8. Make external I/O bounded by timeouts and typed failures; make retryable jobs idempotent.
9. Add behavior-oriented domain/application tests and real integration coverage where persistence or wiring matters.
10. Run backend quality checks and review imports, transaction lifetime, query bounds, file size, and final diff.

For broad backend changes, delegate independent read-only architecture and test-gap reviews. Give subagents the same applicable instructions and this skill.
