# PostGIS release checks

The canonical Compose stack runs PostgreSQL 17 with PostGIS 3.5 from an
immutable image digest. The image only supplies the extension binaries;
Alembic owns `CREATE EXTENSION postgis` and all schema changes. Do not add
database initialization scripts that bypass the migration history.

## Network and runtime contract

- Base and production publish no PostgreSQL port. The database is reachable
  only as `postgres:5432` on the internal `data` network.
- The development override publishes PostgreSQL on loopback only
  (`127.0.0.1:${POSTGRES_PORT:-5432}`).
- PostgreSQL runs as explicit UID/GID `70:70`, with all capabilities dropped,
  `no-new-privileges`, a read-only root filesystem, bounded resources and
  bounded JSON logs. Its data directory is the named `postgres_data` volume.
- `migrate` is a non-restarting one-shot service. API and worker startup stays
  blocked until it completes successfully.

Render all deployment variants before release:

```bash
docker compose -f infra/compose.yaml config --quiet
docker compose -f infra/compose.yaml -f infra/compose.dev.yaml config --quiet
docker compose -f infra/compose.yaml -f infra/compose.prod.yaml config --quiet
```

Inspect the effective database user and published ports without starting it:

```bash
docker compose -f infra/compose.yaml config --format json | jq '.services.postgres | {user, ports, networks, read_only, cap_drop, security_opt}'
docker compose -f infra/compose.yaml -f infra/compose.prod.yaml config --format json | jq '.services.postgres | {user, ports, networks}'
```

## Migration and extension probe

Run the release migration, then query extension availability from inside the
private network:

```bash
docker compose -f infra/compose.yaml run --rm migrate
docker compose -f infra/compose.yaml exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT extversion FROM pg_extension WHERE extname = '\''postgis'\'';"'
```

The probe must return one PostGIS version. An empty result means the migration
that creates the extension has not run; image availability alone is not enough.
Clean-database and current-database Alembic upgrade checks remain release-gate
work owned by the migration integrator.

## First-admin bootstrap

After migrations succeed, run the opt-in release profile with the bootstrap
email and a host path to a UTF-8 password file. Only the one-shot container
receives the mounted secret; API, worker and frontend do not.

```bash
ADMIN_BOOTSTRAP_EMAIL=admin@example.com \
ADMIN_BOOTSTRAP_PASSWORD_FILE=/absolute/path/to/admin-password \
docker compose -f infra/compose.yaml --profile bootstrap run --rm bootstrap-admin
```

Re-running the command leaves an existing admin and password unchanged. A
conflicting non-admin account fails without changing it. Never place the
password itself in Compose, environment values, command arguments or logs.

## Host `operation not permitted` diagnosis

On the current development host, hardened containers fail before their
entrypoints execute, including unrelated PostgreSQL, Redis, RabbitMQ and
frontend images. Docker reports:

```text
exec /usr/local/bin/docker-entrypoint.sh: operation not permitted
```

The affected containers retain `no-new-privileges:true`; removing that control
is not an accepted fix. Diagnose the host runtime/security policy (Docker
daemon logs, AppArmor/SELinux/audit events, seccomp/runtime versions, and the
backing filesystem mount flags), then rerun the probes above. This failure
happens before application or migration code starts.
