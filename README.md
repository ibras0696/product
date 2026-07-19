# Product Hackathon Foundation

Production-oriented single-server foundation with FastAPI, PostgreSQL, Redis, RabbitMQ, Celery, React, Nginx, and Certbot.

## Local start

```bash
cp .env.example .env
# Replace development passwords in .env.
docker compose -f infra/compose.yaml -f infra/compose.dev.yaml up -d --build
make seed-research-demo
```

The local start loads the complete `docs/test/` research snapshot into the same
catalog used by the application, so the map, chronology, source evidence, and
relation graph are populated immediately. The owner-approved demo command publishes
the candidates and their source links while retaining every `needs_review` marker.
This shortcut is local-only and must not be used for a production seed.

To import the same research set as unpublished drafts with unverified sources,
run `make seed-research` instead. Both commands generate and load ordered internal
batches capped at 1,000 records and 2 MB per transaction; rerunning either command
is idempotent and does not require wiping the catalog.

Open `http://localhost:8080`. API docs are at `http://localhost:8080/api/docs`; RabbitMQ management is available only in development at `http://127.0.0.1:15672`.

## Container security

All runtime containers use explicit non-root UID/GID values. The API, worker, migrations, databases, queues, Nginx, frontend, and Certbot also run with all Linux capabilities dropped, `no-new-privileges`, and read-only root filesystems. Only their declared volumes and temporary filesystems are writable.

The Docker build stages still use root where image construction requires installing packages or creating users. This privilege exists only while the image is being built; application processes and infrastructure services never start as root.

## Production TLS bootstrap

1. Point the domain A/AAAA records to the server and set `DOMAIN` and `CERTBOT_EMAIL` in `.env`.
2. Start the HTTP configuration on public port 80: `HTTP_PORT=80 docker compose -f infra/compose.yaml up -d gateway`.
3. Request the first certificate: `docker compose -f infra/compose.yaml --profile tls-init run --rm --build certbot-init`.
4. Start production with renewal: `docker compose -f infra/compose.yaml -f infra/compose.prod.yaml --profile tls up -d --build`.
5. Test renewal: `docker compose -f infra/compose.yaml --profile tls run --rm certbot-renew certbot renew --dry-run`.

Back up the PostgreSQL volume and the `certbot_certs` volume. A backup is not accepted until a restore drill succeeds.
