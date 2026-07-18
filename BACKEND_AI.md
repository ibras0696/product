# Backend AI: план реализации «Паутины истории Чечни»

Статус: обязательный execution brief для Backend AI и backend-субагентов.

Входы: `TZ.md`, `docs/api-contracts.md`, локальные Claude/Codex rules и skills.

## 1. Цель и границы

Backend должен реализовать проверяемый каталог исторических сущностей и связей, bounded
map/search/graph API, защищённые публичные заявки, безопасные media uploads и атомарную
модерацию.

Backend не создаёт новый проект и не заменяет существующие auth, health, UoW, exception,
Compose и quality-gate решения без доказанной необходимости. SQLite, Neo4j, Elasticsearch,
новые очереди и LLM-функции не входят в MVP.

## 2. Обязательные правила каждого агента

Перед действием агент полностью читает применимые локальные правила и skills, затем
проверяет существующий код, тесты, конфигурацию и Git diff.

- Архитектура: modular monolith, DDD-lite, KISS/YAGNI/SOLID/DRY.
- Зависимости: `routes → service`; service независимо использует domain и repository/UoW;
  `repository → models`. Domain не импортирует repository, ORM или infrastructure.
- Pydantic schemas существуют на границе routes/service; domain не импортирует framework/I/O.
- Routes содержат только HTTP; service оркестрирует; domain хранит правила; repository — SQL.
- Repository не авторизует и не commit; один use case — один commit через Unit of Work.
- Каждый endpoint возвращает `ApiResponse[T]`; raw `HTTPException` запрещён.
- External/file I/O имеет timeout/limits и typed failure; retryable operation идемпотентна.
- Query всегда bounded; запрещены N+1, blocking I/O в async, hidden dependencies и mutable globals.
- Файл целится в <300 строк, review после 400, hard limit 600; функция <40, hard limit 80.
- Тестируется observable scenario, а не по одному тривиальному тесту на функцию.
- Агент не ослабляет lint/type/tests/import boundaries/permissions ради зелёного результата.
- Секреты и production data не читаются, не печатаются и не попадают в diff/logs.

Любое изменение endpoint сначала сверяется с `docs/api-contracts.md`. Реализованный slice
одновременно обновляет Pydantic/OpenAPI, generated TS client, frontend adapter и tests.

## 3. Владение bounded contexts

```text
backend/src/modules/
├── auth/          # существующие accounts, sessions; добавить RBAC/public contracts
├── catalog/       # public + admin entities/relations/sources, map/search/graph/export
├── submissions/   # draft ownership, submit, tracking status, status history
├── media/         # validation, storage port, preview, draft/published lifecycle
└── moderation/    # queue, claim, publish/reject/revision, audit
```

`map`, `search` и `graph` — query use cases `catalog`, а не отдельные bounded contexts.
Модули импортируют только публичные application contracts или обмениваются явными events.
Deep imports в чужие repositories/models запрещены.

Толстый модуль повторяет структуру:

```text
modules/catalog/
├── routes.py
├── schemas.py
├── service.py                 # тонкий фасад
├── services/                  # split по use case около 300 строк
├── domain/
├── repository.py             # split queries/ при необходимости
├── models.py
├── public.py                  # минимальные межмодульные contracts
└── tests/
```

Media storage реализуется adapter-ом: local Docker volume в MVP. S3 adapter не создаётся до
решения о миграции. PostGIS принадлежит infrastructure persistence, не domain.

## 4. Доменные инварианты

- published entity и relation имеют минимум один verified source;
- relation не соединяет entity с собой;
- public queries никогда не возвращают draft/archived/private content;
- submission status меняется только по state machine из `TZ.md`;
- owner может исправить `draft` и `needs_revision`, затем повторно отправить в `pending`;
- UUID draft не является правом доступа; ownership проверяется по server-side capability;
- media проходит signature/decode/size/dimensions validation до постоянного сохранения;
- retry upload использует обязательный idempotency key и не создаёт duplicate media;
- publish проверяет role, expected version, idempotency key и все content rules;
- publish result + audit + submission transition фиксируются одним commit или откатываются;
- unknown role/permission denied;
- AI output не является историческим источником.

## 5. Модель данных MVP

Минимальные группы таблиц:

- catalog: entities, localized/alternative names, relations, sources и explicit link tables;
- media: metadata, storage key, checksum, lifecycle status, entity/submission links;
- submissions: draft content, opaque tracking lookup hash, version, status history;
- moderation: claim/decision audit и idempotency record;
- auth: существующие accounts/sessions плюс roles/account_roles.

Coordinates — PostGIS geography/geometry с пространственным индексом. PostgreSQL constraints
защищают уникальность slug, self-relation, допустимые статусы и version. JSONB допускается
только для действительно изменяемых localized/предложенных данных, не вместо модели.

Миграции:

- создаются Alembic и проверяются на чистой и текущей базе;
- имя revision: `NNNN_MM_YYYY_short_name`, например `0003_07_2026_catalog_core`;
- применённая миграция не редактируется;
- PostGIS extension и schema changes имеют явный downgrade там, где он безопасен;
- seed отделён от миграций и содержит только подтверждённый контент с источниками.

## 6. Работа Backend Lead и субагентов

Backend Lead владеет планом, central integration, public boundaries, OpenAPI sync и финальным
quality gate. Субагенты применяются только к независимым bounded work items.

| Роль | Bounded ownership | Не трогает |
| --- | --- | --- |
| Catalog Agent | `modules/catalog/**`, catalog migrations/tests | submissions/media/moderation internals |
| Submission Agent | `modules/submissions/**`, draft/status tests | catalog persistence и auth internals |
| Media Agent | `modules/media/**`, storage/validation tests | moderation decisions и Nginx |
| Moderation Agent | `modules/moderation/**`, public contracts, audit tests | чужие repositories/models |
| Auth/Security Reviewer | read-only auth/RBAC/ownership/upload review | production secrets и unrelated code |
| Backend QA Reviewer | read-only scenario/import/query/test-gap review | implementation writes |
| Infra Agent | PostGIS image/Compose/migration release changes | feature business logic |

Один файл имеет одного writing owner. Общие router, OpenAPI artifact, dependency lock и
migration chain интегрирует Backend Lead последовательно. Каждый handoff содержит outcome,
changed paths, acceptance evidence, validation, risks и next action.

## 7. Вертикальные slices

Один slice — одна исполняемая пачка/спринт. Его нельзя закрыть частично: задачи, slice gate и
общий backend gate должны быть отмечены вместе.

### 7.1. Как вести чек-лист

- `[ ]` — задача не подтверждена; `[x]` ставится только после code review и evidence.
- Перед пачкой Lead записывает: `status`, `owner`, `branch/worktree`, `owned paths`, `subagents`.
- Допустимые статусы: `ready`, `running`, `review`, `blocked`, `done`.
- Один writing owner на файл; router, OpenAPI, dependency lock и migration chain меняет Lead.
- Следующий slice не начинается, пока batch gate текущего не завершён.
- Subagent возвращает changed paths, выполненные AC, команды/результаты, риски и следующий шаг.

Карточка пачки:

```text
Status: ready
Owner:
Branch/worktree:
Owned paths:
Subagents:
Acceptance evidence:
Skipped checks / blockers:
```

### 7.2. Обязательный backend gate после каждой пачки

- [ ] Сверены `TZ.md` и `docs/api-contracts.md`; contract drift отсутствует.
- [ ] Добавлены сценарные тесты: happy path, главный invariant, failure и authorization.
- [ ] Проверены UoW commit/rollback, bounded queries, timeout/idempotency и отсутствие N+1.
- [ ] Проверены imports, размеры файлов/функций, diff и отсутствие secrets/silent disables.
- [ ] Узкий набор тестов изменённого модуля прошёл.
- [ ] Полный backend quality image собран командой ниже.
- [ ] Read-only reviewer подтвердил архитектуру и test gaps либо замечания исправлены.
- [ ] Lead записал evidence и только после этого отметил slice как `done`.

```bash
python3.13 scripts/validate_ai_harness.py
python3.13 scripts/check_file_sizes.py
python3.13 scripts/check_python_complexity.py
docker build --target quality -t product-hackathon-backend-quality ./backend
git diff --check
```

### Slice 0 — foundation и контракт

- [ ] Зафиксировать public module contracts и import-linter boundaries.
- [ ] Подготовить PostgreSQL/PostGIS image и one-shot migration release path.
- [ ] Перенести auth target на `/api/v1/auth` с совместимым переходом.
- [ ] Добавить RBAC schema/policy без публичного самоназначения роли.
- [ ] Добавить idempotent one-shot bootstrap первого admin: email из
  `ADMIN_BOOTSTRAP_EMAIL`, пароль только из `ADMIN_BOOTSTRAP_PASSWORD_FILE`;
- [ ] В `.env.example` оставить только имена bootstrap settings без значений; bootstrap secret
  не передаётся API/worker/frontend после release step;
- [ ] Нормализовать validation/unexpected errors в `ApiResponse[T]`.
- [ ] Обновить OpenAPI и передать reviewed diff Frontend Lead.
- [ ] Покрыть bootstrap, login/session, denied role и migration regression сценариями.

Подробные задачи Slice 0:

| ID | Владелец и owned paths | Точный результат | Обязательные сценарии/evidence |
| --- | --- | --- | --- |
| BE-0.1 | Backend Lead: `backend/src/router.py`, module `public.py`, import-linter config | Зафиксированы public application contracts; новый модуль подключается только через router/public API; domain imports framework/repository запрещены | Диаграмма imports в handoff, `lint-imports` зелёный, отсутствуют deep cross-module imports |
| BE-0.2 | Infra Agent: `infra/compose*.yaml`, Postgres image/Dockerfile, release docs | PostgreSQL 17 заменён совместимым pinned PostGIS image; extension создаётся миграцией; DB остаётся private/non-root | Base/dev/prod `config --quiet`, clean/current migration, PostGIS probe, effective user/ports evidence |
| BE-0.3 | Auth Agent: `backend/src/modules/auth/**`, auth migration | Target `/api/v1/auth`, совместимый переход со старого prefix, roles/account_roles, deny-by-default permissions | Register/login/me/logout regression; moderator/editor/admin/unknown-role matrix; invalid Origin и expired session |
| BE-0.4 | Auth Agent + Infra integrator: bootstrap service/command и env example | One-shot создаёт первого admin из email + password file, делает один commit и повторно не меняет пароль/роль | First run, second run, existing conflicting account, missing/empty secret; stdout/stderr/diff без credentials |
| BE-0.5 | Platform Agent: common exceptions/schemas, FastAPI handlers | Pydantic/FastAPI/unexpected errors нормализованы в `ApiResponse`; stable codes/status/header semantics совпадают с контрактом | 401/403/404/409/422/429/500/503 API scenarios, request-id correlation, stack trace отсутствует в response |
| BE-0.6 | Backend Lead: OpenAPI artifact и handoff | Target endpoints/schemas/errors присутствуют в OpenAPI; generated frontend client обновляется без ручных типов | Reviewed OpenAPI diff, generation command/result, список временно не реализованных target endpoints |

Gate Slice 0:

- [ ] Clean/current database migrations и `alembic check` проходят.
- [ ] Base/dev/prod Compose render без ошибок; PostGIS доступен только private network.
- [ ] Bootstrap повтор не меняет существующего admin и не выводит secret.
- [ ] Auth regression и unknown-role deny проходят.
- [ ] OpenAPI/generated-client diff согласован с Frontend Lead.

### Slice 1 — catalog map и entity

- [ ] Реализовать entity/relation/source domain rules и persistence.
- [ ] Запретить self relation и публикацию entity/relation без verified source.
- [ ] Создать миграции, constraints, spatial/search indexes и verified seed pipeline.
- [ ] Реализовать bounded bbox map query и published-only scope.
- [ ] Реализовать entity details, sources и published media endpoints.
- [ ] Реализовать catalog options для districts, periods и entity types.
- [ ] Исключить N+1 и проверить deterministic ordering.

Подробные задачи Slice 1:

| ID | Владелец и owned paths | Точный результат | Обязательные сценарии/evidence |
| --- | --- | --- | --- |
| BE-1.1 | Catalog Agent: `modules/catalog/domain/**` | Entity, relation, source и publication policy выражены чистыми domain-правилами; self relation/source invariants не зависят от БД | Entity/relation publication happy path, missing source, self relation, oral testimony classification |
| BE-1.2 | Catalog Agent: models/repository + новая migration | Нормализованные catalog tables, FK/check/unique constraints, PostGIS coordinate, archive/status/version fields и индексы | Clean upgrade/downgrade where safe, constraint violations, optimistic version, spatial index existence |
| BE-1.3 | Catalog Agent: seed command/data | Idempotent seed загружает только проверенные entities/relations/sources с provenance и стабильными IDs/slugs | First/repeated seed, missing source rejected, row/link counts, никакой генерации фактов через AI |
| BE-1.4 | Catalog Agent: map query service/repository/routes/schemas | `GET /map/entities` валидирует bbox/zoom/limits, использует spatial index, возвращает published points и truncation | Invalid bbox/period, empty, filters, hard limit, archived/private exclusion, deterministic ordering |
| BE-1.5 | Catalog Agent: entity/source/media query use cases | Details и bounded child lists возвращают локализацию/counts/public URLs без internal keys и N+1 | Published details, hidden draft/archive, missing entity, empty media/sources, query-count evidence |
| BE-1.6 | Catalog Agent: options query | Districts, periods и entity types берутся из backend source of truth, имеют stable IDs и ETag | Empty/filled options, conditional request, unknown district rejected by consuming endpoints |

Gate Slice 1:

- [ ] BR-001–BR-004 доказаны domain/integration tests.
- [ ] Bbox validation, empty result, 404, truncation и published scope проверены.
- [ ] Query plan использует нужные индексы на реалистичном seed.
- [ ] Map/entity/source/media schemas совпадают с OpenAPI.

### Slice 2 — graph и search

- [ ] Реализовать graph depth 1–2 и hard limit 40.
- [ ] Добавить dedup nodes/edges, cycle handling и hidden count.
- [ ] Реализовать filters по type/period без unbounded traversal.
- [ ] Реализовать PostgreSQL full-text/trigram search по RU/CE/alternative names.
- [ ] Добавить deterministic ordering и bounded pagination.
- [ ] Измерить p95 на agreed dataset/server profile.

Подробные задачи Slice 2:

| ID | Владелец и owned paths | Точный результат | Обязательные сценарии/evidence |
| --- | --- | --- | --- |
| BE-2.1 | Catalog Graph Agent: graph domain/query service/repository | Bounded traversal depth 1–2 формирует center/nodes/edges, dedup и hidden count без загрузки всего графа | No relations, cycle, duplicate paths, depth 1/2, hard limit 40, hidden count correctness |
| BE-2.2 | Catalog Graph Agent: graph schemas/routes | Filters type/period применяются согласованно к nodes/edges; каждый edge указывает на center/existing node | Invalid filters, filtered edge integrity, missing center, stable ordering, contract/OpenAPI match |
| BE-2.3 | Search Agent: names persistence/index migration | RU/CE/alternative/historical names индексируются PostgreSQL FTS/trigram без отдельного search service | Index migration, normalization/case, duplicate alternative names, explain-plan evidence |
| BE-2.4 | Search Agent: search service/repository/routes | Search валидирует q/limit/offset, ранжирует детерминированно и возвращает bounded published results | Exact/typo/CE/alternative query, empty, archive exclusion, combined filters, offset boundary |
| BE-2.5 | Backend QA: performance fixture/measurement docs | Зафиксированы dataset size, server profile, concurrency и p50/p95 для graph/search; измерение воспроизводимо | Команда/результат в handoff, отсутствие unbounded scan/N+1, отклонение от NFR оформлено blocker-ом |

Gate Slice 2:

- [ ] Cycle/dedup/depth/limit/filter/empty/404 scenarios проходят.
- [ ] Typo, alternative name, CE/RU и pagination search scenarios проходят.
- [ ] Graph/search query plans не содержат N+1/unbounded scans.
- [ ] Зафиксирован latency result и dataset, на котором он получен.

### Slice 3 — submissions и media

- [ ] Реализовать server-side draft ownership и random tracking capability.
- [ ] Реализовать create/update/submit/status и `needs_revision→pending`.
- [ ] Запретить доступ к draft/media по одному UUID из чужой сессии.
- [ ] Реализовать streaming bounded upload и фактическую MIME/decode проверку.
- [ ] Добавить dimensions/size limits, EXIF removal и WebP preview.
- [ ] Добавить upload idempotency key и checksum.
- [ ] Реализовать rollback partial files и bounded orphan cleanup.
- [ ] Не писать tracking code, contacts и file content в logs.

Подробные задачи Slice 3:

| ID | Владелец и owned paths | Точный результат | Обязательные сценарии/evidence |
| --- | --- | --- | --- |
| BE-3.1 | Submission Agent: submission domain/models/migration | SubmissionType/state/version/history и state machine `draft↔needs_revision→pending→in_review` реализованы без invalid jumps | Каждый допустимый переход, forbidden transition, optimistic conflict, history ordering |
| BE-3.2 | Submission Agent: capability/token service/repository | Draft ownership и tracking lookup используют независимые high-entropy secrets/hashes; UUID не авторизует | Owner/attacker sessions, guessed UUID, invalid tracking, rate limit, raw secret отсутствует в DB/logs |
| BE-3.3 | Submission Agent: routes/schemas/services | Create/PATCH/submit/status реализуют exact discriminated request fields; revision редактируется и отправляется повторно | Все SubmissionType, partial PATCH/null semantics, consent/required fields, submit replay |
| BE-3.4 | Media Agent: storage port/local adapter | Streaming upload пишет temp file с bounds/timeouts, атомарно перемещает после проверки и возвращает typed failure | Client disconnect, disk error, oversized body, timeout, temp cleanup; storage path не управляется input |
| BE-3.5 | Media Agent: validator/preview pipeline | MIME определяется по signature+decode; JPEG/PNG/WebP limits, dimensions, decompression protection, EXIF removal и preview | Spoofed extension, corrupt image, bomb dimensions, valid formats, preview metadata, EXIF absent |
| BE-3.6 | Media Agent: idempotency repository/service | Один `Idempotency-Key`+payload возвращает тот же media; другой payload конфликтует; checksum фиксируется | Lost response retry, concurrent same key, same content/different key policy, no duplicate file/row |
| BE-3.7 | Maintenance owner: orphan cleanup use case | Cleanup выбирает только expired unreferenced draft media bounded page-ами и безопасен при повторе | Referenced/published files preserved, partial failure retry, max batch, audit/metrics без PII |

Gate Slice 3:

- [ ] Owner/attacker, draft/revision, submit retry и expired capability scenarios проходят.
- [ ] Lost-response upload retry возвращает прежний media без дубля.
- [ ] Invalid/oversized/decompression-bomb media не сохраняется.
- [ ] Multi-file partial failure не повреждает успешные uploads и не оставляет мусор.

### Slice 4 — moderation и publication

- [ ] Реализовать bounded queue, claim и optimistic version.
- [ ] Реализовать publish/reject/request revision permissions.
- [ ] Реализовать discriminated publish action для каждого `SubmissionType`.
- [ ] Выполнить catalog result, selected media, status и audit одним UoW commit.
- [ ] Добавить idempotency/conflict handling для moderation commands.
- [ ] Реализовать admin catalog read/create/update/archive с audit.
- [ ] Реализовать bounded allowlisted streaming JSON/CSV export.
- [ ] Выполнять cache invalidation только после успешного commit.

Подробные задачи Slice 4:

| ID | Владелец и owned paths | Точный результат | Обязательные сценарии/evidence |
| --- | --- | --- | --- |
| BE-4.1 | Moderation Agent: queue/claim services/repository/routes | Bounded queue filters, claim ownership и expected version предотвращают silent overwrite | Empty/filtered pages, two moderators claim, stale version, forbidden actor, deterministic pagination |
| BE-4.2 | Moderation Agent: discriminated commands/schemas | Для каждого SubmissionType разрешён только согласованный PublishAction/payload; unknown/mismatch rejected | Six type/action happy paths, mismatch, unknown fields, missing source/media, safe error code |
| BE-4.3 | Moderation + Catalog integrator: publish service/UoW | Catalog changes, selected media, submission status, idempotency record и audit выполняются одним commit | Injected failure на каждом внешнем шаге, full rollback, replay same/different payload, public visibility after commit |
| BE-4.4 | Moderation Agent: reject/revision services | Reject/revision требуют permission, expected version и non-empty public/internal comment policy | Concurrent decision, empty comment, revision returned to owner, unauthorized and already-final submission |
| BE-4.5 | Catalog Admin Agent: admin query/command routes | Editor/admin list/create/update/archive entities/relations/sources; moderator read scope ограничен policy | Role matrix, source invariants, version conflicts, archive/public exclusion, audit for every mutation |
| BE-4.6 | Export Agent: export query/stream adapter | JSON/CSV export использует explicit field allowlist, ≤10k rows/100 MiB, streaming и safe filename | Published/all role matrix, empty export, size limit, disconnect, CSV injection escaping, no PII/secrets/internal keys |
| BE-4.7 | Integration owner: post-commit hooks | Cache invalidation/event выполняется после commit и не делает transaction partial при сбое | Commit failure emits nothing, invalidation failure preserves DB truth, subsequent read/retry consistent |

Gate Slice 4:

- [ ] Unauthorized/unknown-role bypass запрещён backend policy.
- [ ] Concurrent moderators получают version conflict без потери данных.
- [ ] Publish failure откатывает catalog/media/status/audit полностью.
- [ ] Replay не создаёт дубликаты; разные payload с одним key конфликтуют.
- [ ] Archive исчезает из public API, но остаётся в admin/audit.
- [ ] Export не содержит credentials, sessions, contacts и internal storage keys.

### Slice 5 — release readiness

- [ ] Синхронизировать OpenAPI/client/adapters.
- [ ] Прогнать full backend и cross-stack critical scenarios.
- [ ] Проверить migration на production-like структуре без чтения production data.
- [ ] Провести backup/restore rehearsal.
- [ ] Проверить non-root runtime users, health, private ports и Nginx syntax.
- [ ] Собрать versioned offline `chechnya.pmtiles` artifact с provenance/license manifest и
  обязательной OSM attribution; runtime не загружает внешние tiles.
- [ ] Зафиксировать startup, failed-migration и rollback procedure.

Подробные задачи Slice 5:

| ID | Владелец и owned paths | Точный результат | Обязательные сценарии/evidence |
| --- | --- | --- | --- |
| BE-5.1 | Backend Lead: OpenAPI/client integration | Runtime OpenAPI, canonical contract, generated client и frontend adapters синхронны; compatibility workaround удалён/задокументирован | Clean generation diff, endpoint inventory, contract scenario report |
| BE-5.2 | Database/Infra Agent: release migration + backup docs/scripts | Migration one-shot завершается до API; backup PostgreSQL/media восстанавливается в isolated environment | Clean/current upgrade, failed migration leaves old app viable, restore row/media/checksum smoke |
| BE-5.3 | Infra Agent: Compose/Nginx/runtime inspection | Production publishes только 80/443; all containers explicit non-root, read-only/drop caps/resource/log bounds where supported | Rendered configs, `id` evidence, Nginx `-t`, health, private DB/Redis/Rabbit ports |
| BE-5.4 | Offline Artifact Agent: PMTiles build manifest | Reproducible versioned Chechnya extract содержит source date/checksum/license/attribution и не требует runtime tile network | Rebuild checksum or documented variance, offline network trace, attribution visible, artifact size recorded |
| BE-5.5 | Lead + QA reviewers: release evidence | Full quality gate, critical E2E/a11y, migration/restore/security review и known risks собраны в release handoff | Команды с exit status, skipped checks, rollback commit/images, owner approval; никаких секретов в evidence |

Gate Slice 5:

- [ ] `./scripts/quality_gate.sh` полностью зелёный.
- [ ] OpenAPI/generated client имеют reviewed synchronized diff.
- [ ] Backup восстановлен в отдельную test database и проверен smoke queries.
- [ ] Production Compose публикует только Nginx 80/443 и все runtime users non-root.
- [ ] Offline read-only flow работает без network requests.
- [ ] Release notes содержат migrations, known risks и rollback decision.

## 8. Test strategy

- Domain: source requirement, self relation, status transitions и publish invariants.
- Application: один полный use case с UoW commit/rollback и deterministic fakes только для
  storage/clock/token generator.
- Integration: реальный PostgreSQL/PostGIS для queries, constraints, migrations и concurrency.
- API: envelope, validation, permissions, ownership, rate limit, idempotent upload и errors.
- E2E: map→graph→source, revision submission, moderator publication, admin catalog/export.

Не создавать отдельный тест на каждый getter/schema. Один сценарий вправе доказать несколько
связанных функций и инвариантов.

## 9. Definition of Done

- use case, invariant, owner, failure и transaction boundary записаны;
- API соответствует canonical contract и OpenAPI/client синхронизированы;
- domain не зависит от framework/I/O, service/repository разделены;
- relevant behavior tests, PostgreSQL integration и auth scenario зелёные;
- Ruff format/check, mypy, import-linter, migrations, Pytest и Docker build проходят;
- queries/limits/timeouts/file sizes проверены;
- final diff не содержит секретов, dead code, silent disables и unrelated rewrites;
- skipped checks и model/content uncertainty сообщены явно.
