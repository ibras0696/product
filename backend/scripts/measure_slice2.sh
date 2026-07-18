#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
compose_file="$project_dir/infra/compose.yaml"
base_url=${SLICE2_BASE_URL:-http://127.0.0.1:8080/api/v1}

psql_compose() {
  docker compose -f "$compose_file" exec -T postgres sh -lc \
    'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
}

cleanup() {
  psql_compose <<'SQL'
DELETE FROM catalog_relations
 WHERE id IN (SELECT md5('perf-r-'||g)::uuid FROM generate_series(1,50000) g);
DELETE FROM catalog_entity_names
 WHERE id IN (SELECT md5('perf-n-'||g)::uuid FROM generate_series(1,30000) g);
DELETE FROM catalog_entity_texts
 WHERE id IN (SELECT md5('perf-t-'||g)::uuid FROM generate_series(1,10000) g);
DELETE FROM catalog_entities WHERE slug LIKE 'perf-e-%';
SQL
}
trap cleanup EXIT INT TERM

psql_compose <<'SQL'
INSERT INTO catalog_entities (id,type,slug,status,version,period_from,period_to)
SELECT md5('perf-e-'||g)::uuid,
       CASE WHEN g%2=0 THEN 'settlement' ELSE 'person' END,
       'perf-e-'||g,'published',1,1800+(g%200),2000
  FROM generate_series(1,10000) g;
INSERT INTO catalog_entity_texts
       (id,entity_id,locale,title,short_description,full_description)
SELECT md5('perf-t-'||g)::uuid,md5('perf-e-'||g)::uuid,
       'ru','Объект '||g,'История '||g,'Описание '||g
  FROM generate_series(1,10000) g;
INSERT INTO catalog_entity_names (id,entity_id,locale,name)
SELECT md5('perf-n-'||g)::uuid,md5('perf-e-'||((g-1)%10000+1))::uuid,
       'ru','Альтернатива '||g
  FROM generate_series(1,30000) g;
INSERT INTO catalog_relations
       (id,source_entity_id,target_entity_id,type,title_ru,description_ru,status,version)
SELECT md5('perf-r-'||g)::uuid,
       md5('perf-e-'||((g-1)%10000+1))::uuid,
       md5('perf-e-'||(((g-1)%10000+1)%10000+1))::uuid,
       'connected_with','Связь','Описание','published',1
  FROM generate_series(1,50000) g;
ANALYZE catalog_entities;
ANALYZE catalog_entity_texts;
ANALYZE catalog_entity_names;
ANALYZE catalog_relations;
SQL

center_id=$(psql_compose <<'SQL'
SELECT md5('perf-e-1')::uuid;
SQL
)
center_id=$(printf '%s\n' "$center_id" | awk '/^[0-9a-f-]{36}$/{print; exit}')

measure() {
  url=$1
  label=$2
  timings=$(mktemp)
  for _ in $(seq 1 100); do
    curl -fsS -o /dev/null -w '%{time_total}\n' "$url" >>"$timings"
  done
  sort -n "$timings" | awk -v label="$label" \
    'NR==50{p50=$1} NR==95{print label, "p50_seconds="p50, "p95_seconds="$1}'
  rm -f "$timings"
}

measure "$base_url/entities/$center_id/graph?depth=2&limit=40" graph
measure "$base_url/search?q=%D0%9E%D0%B1%D1%8A%D0%B5%D0%BA%D1%82%205000&limit=20" search
