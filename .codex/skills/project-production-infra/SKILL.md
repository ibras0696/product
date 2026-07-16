---
name: project-production-infra
description: Design, implement, review, or deploy this repository's Docker Compose, Dockerfiles, Nginx, Certbot, PostgreSQL, Redis, RabbitMQ, Celery, backups, CI, observability, or single-server production infrastructure. Use for every infrastructure, deployment, container, proxy, TLS, or operations change.
---

# Project Production Infrastructure

1. Read the active platform contract in `.codex/config.toml` or `.claude/CLAUDE.md` and load `docker-development`; use `slo-architect` only when reliability targets or alerts are in scope.
2. Keep `infra/compose.yaml` canonical and its dev/prod overrides minimal.
3. Draw the trust/network boundary and expose only what is required.
4. Pin images, use multi-stage builds and non-root runtime users, add health checks, explicit dependencies, resource/log bounds, and named volumes.
5. Keep secrets out of images, Compose values, logs, history, and examples.
6. Treat migrations as a one-shot release step. Define startup, rollback, and failure behavior.
7. For TLS, verify challenge path, certificate persistence, renewal, and Nginx reload.
8. For stateful services, document backup, retention, restore, and data-loss risks.
9. Validate Dockerfiles, render Compose configuration, inspect published ports/networks/volumes, and test Nginx configuration where available.
10. Do not add orchestration or observability complexity without a concrete operating requirement.

Use a read-only security/reliability subagent for production-impacting changes. The main agent owns the deployment decision and rollback plan.
