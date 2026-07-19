# Production release runbook

This runbook covers the single-server Compose release. Run commands from the repository root.
Never place passwords in command arguments, logs, backup names, or release evidence.

## Preconditions

- DNS points to the host and the TLS bootstrap from `README.md` has completed.
- `.env` is readable only by the deployment account and contains production credentials.
- `IMAGE_TAG` identifies an immutable release; record resolved image digests in the release note.
- `BACKUP_ROOT` is an encrypted host filesystem outside the repository and has sufficient space.
- The previous application image remains available until the release is accepted.

Render and inspect the release without printing container environments:

```bash
docker compose -f infra/compose.yaml config --quiet
docker compose -f infra/compose.yaml -f infra/compose.dev.yaml config --quiet
docker compose -f infra/compose.yaml -f infra/compose.prod.yaml config --quiet
docker compose -f infra/compose.yaml -f infra/compose.prod.yaml config --format json \
  | jq '.services | with_entries(.value |= {image,user,ports,read_only,cap_drop,security_opt,volumes})'
```

## Backup and restore gate

Create a consistent PostgreSQL dump and media archive before migration:

```bash
BACKUP_ROOT=/srv/product-backups infra/scripts/backup.sh
```

First drain write traffic and background jobs for the bounded backup window. PostgreSQL and media
are separate persistence systems, so an online copy while uploads or deletions continue is not an
accepted matched backup set. Restore service immediately if backup fails.

`backup.sh` uses the credentials already present inside PostgreSQL, never copies them to command
arguments, writes files with restrictive permissions, and records SHA-256 checksums. Copy the
completed backup to separate storage according to the retention policy before continuing.

Restore the backup into an isolated Compose project. This never attaches production volumes:

```bash
BACKUP_SET=/srv/product-backups/YYYYMMDDTHHMMSSZ \
RESTORE_PROJECT=product_restore_release_candidate \
infra/scripts/restore_rehearsal.sh
```

The rehearsal verifies archive checksums, Alembic/PostGIS presence, media object existence, and
original media checksums recorded in the database. It removes the isolated project and volumes by
default. Use `KEEP_RESTORE=1` only for a bounded investigation and remove it afterward.

Recommended minimum retention is seven daily and four weekly backups. Set the final retention,
off-host copy, RPO, and RTO with the system owner before production launch. Certificate volume
backup is separate from the application data backup and must follow the same off-host policy.

## Startup and migration

1. Build immutable API/frontend/Certbot images and record their digests.
2. Run the backup and successful isolated restore gate above.
3. Start dependencies without replacing the current API:

   ```bash
   docker compose -f infra/compose.yaml -f infra/compose.prod.yaml up -d postgres redis rabbitmq
   ```

4. Run the release migration explicitly and require exit code zero:

   ```bash
   docker compose -f infra/compose.yaml -f infra/compose.prod.yaml run --rm migrate
   ```

5. Confirm the current revision and schema drift:

   ```bash
   docker compose -f infra/compose.yaml run --rm --no-deps api alembic current
   docker compose -f infra/compose.yaml run --rm --no-deps api alembic check
   ```

6. Start API, worker, frontend, gateway, and the remaining declared services:

   ```bash
   docker compose -f infra/compose.yaml -f infra/compose.prod.yaml up -d --no-deps api worker frontend
   docker compose -f infra/compose.yaml -f infra/compose.prod.yaml up -d --wait --no-deps api frontend
   docker compose -f infra/compose.yaml -f infra/compose.prod.yaml up -d --no-deps gateway
   ```

7. Verify gateway, API readiness, worker health, public critical scenarios, and logs before marking
   the release accepted.

The `migrate` service is non-restarting and API/worker dependencies require its successful
completion during a full-stack startup. The explicit sequence above keeps migration failure from
replacing the old application containers.

## Failed migration

If migration exits non-zero, stop the release. Do not start the new API or edit an applied
migration. Capture only sanitized migration diagnostics. Keep the previous application image and
containers serving traffic if their schema remains compatible. Investigate against the isolated
restore, create a new corrective migration, and repeat backup/restore/migration gates.

If a migration committed a backward-incompatible change before failing, do not guess at a
downgrade. Enter maintenance mode and restore PostgreSQL and media from the matched backup set.
Record the data-loss window and owner decision.

## Forward rollback

Application rollback means redeploying the recorded previous image against a schema explicitly
verified as backward-compatible. Database rollback is forward-only: create a corrective migration.
Use Alembic downgrade only when that exact downgrade was rehearsed and the release owner accepts
its data-loss implications. Never restore PostgreSQL without restoring the media archive from the
same backup set.

## Certificate renewal

Schedule this host-side command with systemd or cron. It uses the Certbot and gateway containers
without a Docker socket mount, validates Nginx, and reloads it after renewal:

```bash
infra/scripts/renew_certificates.sh
```

Test the first schedule invocation manually and alert on a non-zero exit. A successful Certbot exit
without the subsequent Nginx reload is not accepted renewal evidence.

## Release evidence

Record commit, image digests, backup set timestamp, restore rehearsal result, Alembic revision,
Compose inspection, effective non-root users, Nginx syntax, health probes, skipped checks, known
risks, and the rollback image in `docs/releases/`. Never paste `.env`, container environments,
database rows, media names, tokens, or certificate private material.
