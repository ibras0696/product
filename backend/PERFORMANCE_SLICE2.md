# Slice 2 performance evidence

Measured on 2026-07-18 against the canonical local Compose profile through Nginx/API.
The fixture contained 10,000 published entities, 10,000 RU texts, 30,000 alternative
names, and 50,000 published relations. PostgreSQL tables were analyzed before measurement.
All fixture rows used the `perf-` namespace and were deleted after the run.

Each endpoint received 100 sequential warm local HTTP requests; p95 was calculated from
curl `time_total` values sorted numerically:

| Scenario | p50 | p95 |
| --- | ---: | ---: |
| Graph depth 2, limit 40 | 9.205 ms | 18.270 ms |
| Exact RU search, limit 20 | 80.588 ms | 190.118 ms |

The complete deterministic setup, measurement, and scoped cleanup command is:

```bash
sh backend/scripts/measure_slice2.sh
```

It uses `INSERT ... SELECT generate_series(...)` IDs derived with
`md5('perf-e-' || g)::uuid`, the four table counts above, followed by `ANALYZE`. For each URL:

```bash
for i in $(seq 1 100); do
  curl -sS -o /dev/null -w '%{time_total}\n' "$URL"
done | sort -n | awk 'NR==50{p50=$1} NR==95{print "p50=" p50, "p95=" $1}'
```

The run uses concurrency 1 intentionally to record application/query latency without load-test
queueing. Delete only `perf-*` fixture rows after measurement; the recorded run removed 50,000
relations, 30,000 names, 10,000 texts, and 10,000 entities.

The canonical Compose limits at measurement time were API 1 CPU/512 MiB and PostgreSQL
1 CPU/768 MiB. Search integration evidence additionally confirmed Bitmap Index Scan on
the trigram/FTS indexes with a 10,000-row transactional fixture. This local result is not
a production capacity claim; rerun on the release host after restoring the approved seed.
