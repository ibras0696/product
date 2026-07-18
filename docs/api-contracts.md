# API contracts: «Паутина истории Чечни»

Статус: approved target contract for MVP.

Владельцы: backend, frontend, tests, Claude Code и Codex.

Документ хранит общую HTTP-политику и согласованный target-контракт. Реализованным контракт
становится только вертикальный срез, в котором одновременно обновлены Pydantic/OpenAPI,
generated TypeScript client, frontend adapter и сценарные тесты. До миграции auth-среза
текущий runtime `/api/auth/*` остаётся совместимым; целевой путь указан ниже.

## 1. Источники истины и workflow

1. Этот документ владеет решениями, семантикой, правами, ошибками и target endpoints.
2. Pydantic и сгенерированный FastAPI OpenAPI владеют исполняемой HTTP-формой.
3. Сгенерированные TypeScript-типы владеют frontend transport types.
4. Frontend использует generated client только через adapter своего модуля.

Расхождение между документом, OpenAPI, клиентом и runtime — баг. Сгенерированные файлы
вручную не редактируются. Корневого второго API-контракта быть не должно.

## 2. Общий HTTP-контракт

- Базовый target prefix: `/api/v1`.
- JSON: UTF-8, `application/json`, wire fields в `snake_case`.
- Upload: `multipart/form-data` только на указанном endpoint.
- ID — непрозрачный UUID; frontend не извлекает из него смысл.
- Date/time — ISO 8601 UTC с `Z`; исторический период имеет отдельные nullable-поля.
- Optional и nullable различаются и явно отражаются в OpenAPI.
- Все списки и graph/map queries ограничиваются backend-максимумами.
- Клиент может передать `X-Request-ID`; ответ возвращает тот же ID или создаёт новый.
- Автоповтор mutation запрещён без endpoint-specific idempotency contract.

### 2.1. Единый envelope

Каждый JSON endpoint возвращает `ApiResponse[T]`:

```json
{
  "ok": true,
  "data": {},
  "error": null,
  "meta": { "request_id": "opaque-id" }
}
```

Ошибка:

```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "stable_machine_code",
    "message": "Безопасное сообщение",
    "details": null
  },
  "meta": { "request_id": "opaque-id" }
}
```

`ok=true` требует `error=null`; `ok=false` требует `data=null`. Frontend ветвится только по
`error.code`, но не парсит `message`. Успешное удаление возвращает HTTP 200 и `data:null`,
а не 204.

### 2.2. HTTP и базовые ошибки

| HTTP | Код | Значение |
| --- | --- | --- |
| 400 | `bad_request` | семантически неверный запрос |
| 401 | `unauthorized` | нет действующей сессии |
| 403 | `forbidden` | личность известна, права недостаточны |
| 404 | `not_found` | объект не существует или не видим актору |
| 409 | `conflict` | недопустимый переход, версия или повтор |
| 413 | `payload_too_large` | превышен лимит upload/request |
| 415 | `unsupported_media_type` | недопустимый фактический формат файла |
| 422 | `validation_error` | нарушена транспортная схема |
| 429 | `rate_limited` | превышен лимит; присутствует `Retry-After` |
| 500 | `internal_error` | непредвиденная ошибка без внутренних деталей |
| 503 | `service_unavailable` | обязательная зависимость недоступна |

Предметные коды: `source_required`, `self_relation_forbidden`, `invalid_credentials`,
`email_already_registered`, `invalid_origin`, `draft_not_editable`, `invalid_transition`,
`media_rejected`, `idempotency_conflict`.

## 3. Общие типы

```text
LocalizedText = { ru: string, ce: string | null }
Coordinates = { latitude: number[-90..90], longitude: number[-180..180] }
Period = { period_from: integer | null, period_to: integer | null }
PageMeta = { limit: integer, offset: integer, total: integer }
Page[T] = { items: T[], meta: PageMeta }
```

`LocalizedText.ru` обязателен в MVP. Пустая строка не заменяет `null`.

### 3.1. Enum

```text
EntityType = settlement | person | event | landmark | natural_object |
             cultural_object | organization | university_object | artifact

RelationType = born_in | lived_in | worked_in | studied_in | taught_at |
               participated_in | located_in | part_of | created_by |
               described_in | connected_with | connected_with_chgu

SubmissionType = new_entity | update_entity | new_relation | new_source |
                 new_media | report_error

SubmissionStatus = draft | pending | in_review | needs_revision | rejected | published

SourceType = archive_document | book | scientific_article | museum_material |
             official_publication | photo | audio | video | oral_testimony | web_resource

Role = moderator | editor | admin
```

Основные mutation/read models:

```text
SubmissionDraft = {
  id: UUID, type: SubmissionType, related_entity_id: UUID | null,
  settlement_id: UUID | null, title: string, description: string,
  source_description: string, author_name: string, contact: string,
  consent: boolean, status: draft | needs_revision, version: integer,
  tracking_code: string, created_at: datetime, updated_at: datetime
}

SubmissionStatusView = {
  id: UUID, tracking_code: string, type: SubmissionType, title: string,
  status: SubmissionStatus, public_comment: string | null,
  submitted_at: datetime | null, updated_at: datetime
}

SubmissionMedia = {
  id: UUID, submission_id: UUID, original_name: string, mime_type: string,
  size_bytes: integer, width: integer, height: integer, preview_url: string,
  caption: string, author: string, approximate_date: string | null,
  source_description: string, related_entity_id: UUID | null, status: pending
}

PublishResult = {
  submission_id: UUID, status: published, action: PublishAction,
  published_entity_ids: UUID[], published_relation_ids: UUID[],
  published_source_ids: UUID[], published_media_ids: UUID[], audit_id: UUID
}

EntityInput = {
  type: EntityType, slug: string, title: LocalizedText,
  short_description: LocalizedText, full_description: LocalizedText,
  coordinates: Coordinates | null, period_from: integer | null,
  period_to: integer | null, district_id: UUID | null
}

AdminEntity = EntityInput & {
  id: UUID, status: draft | published | archived, version: integer,
  relations_count: integer, sources_count: integer, media_count: integer,
  created_at: datetime, updated_at: datetime
}

EntityPatch = partial EntityInput without `type`; `slug` and localized/period/location fields
may change, but unknown fields are forbidden and `expected_version` is required by mutation.

RelationInput = {
  source_entity_id: UUID, target_entity_id: UUID, type: RelationType,
  title: LocalizedText, description: LocalizedText,
  period_from: integer | null, period_to: integer | null
}

SourceInput = {
  title: string, type: SourceType, author: string | null,
  publisher: string | null, publication_year: integer | null,
  url: string | null, archive_reference: string | null, description: string
}
```

Все поля обязательны, если явно не указано `| null`. PATCH-схемы содержат только разрешённые
изменяемые поля; отсутствие поля означает «не менять», явный `null` — очистить nullable поле.

Enum расширяется только вместе с domain rule, OpenAPI, UI fallback и тестом неизвестного
значения. `approved` отсутствует: publish — атомарное решение MVP.

## 4. Authentication и authorization

Browser auth использует серверную opaque session в cookie:

```text
__Host-product_session=<random token>; Path=/; Secure; HttpOnly; SameSite=Lax
```

Cookie не имеет `Domain`. Raw token не хранится в базе; сохраняется криптографический hash.
Пароль: 12–128 Unicode-символов, Argon2id. Session: 7 дней inactivity, максимум 30 дней.

Unsafe cookie-authenticated запрос проверяет same-origin `Origin`. CORS credentials не
включается без отдельного решения. Роли проверяются backend; неизвестное разрешение denied.

| Endpoint | Auth | Успех |
| --- | --- | --- |
| `POST /api/v1/auth/register` | public | 201 + `CurrentAccount` + cookie |
| `POST /api/v1/auth/login` | public | 200 + `CurrentAccount` + rotated cookie |
| `GET /api/v1/auth/me` | session | 200 + `CurrentAccount` |
| `POST /api/v1/auth/logout` | optional session | 200 + null; idempotent |
| `POST /api/v1/auth/logout-all` | session | 200 + null |
| `GET /api/v1/admin/me` | one admin role | 200 + `AdminAccount` |

```json
{
  "id": "account-uuid",
  "email": "moderator@example.com",
  "status": "active",
  "display_name": "Модератор",
  "roles": ["moderator"]
}
```

Публичная регистрация никогда не назначает административную роль. Назначение роли —
отдельный admin use case с аудитом; его UI не входит в MVP. Invalid login не раскрывает,
существует ли email. Login/register ограничены по source и нормализованному account key.
Первый admin создаётся idempotent one-shot bootstrap release step. Email поступает из
`ADMIN_BOOTSTRAP_EMAIL`, пароль читается только из файла по пути
`ADMIN_BOOTSTRAP_PASSWORD_FILE`. Значения не входят в Git/Compose, command arguments или
логи; bootstrap secret не передаётся постоянным API/frontend containers. После создания
login проверяет Argon2id hash в PostgreSQL, а не ENV.

Admin frontend routes: `/admin/login` и защищённый `/admin/*`. Это client routes того же
frontend bundle; backend API остаётся под `/api/v1/admin/*`.
Admin UI не использует public register: первый admin создаётся bootstrap-операцией, остальные
administrative accounts/roles назначаются только разрешённым admin use case с аудитом.

## 5. Публичный каталог

Публичные endpoints возвращают только `published` данные.
JSON-примеры ниже показывают значение поля `data`; transport всегда добавляет envelope.

### 5.1. Карта

`GET /api/v1/map/entities`

Query:

```text
bbox=min_lon,min_lat,max_lon,max_lat (required)
zoom=integer 5..18 (required)
types=EntityType[]
district_id=UUID
period_from=integer
period_to=integer
limit=1..500 (default 200)
```

```json
{
  "items": [{
    "id": "entity-uuid",
    "type": "settlement",
    "title": { "ru": "Ножай-Юрт", "ce": null },
    "coordinates": { "latitude": 43.092, "longitude": 46.378 },
    "relations_count": 24,
    "cover_url": "/media/entities/cover.webp",
    "district_id": "district-uuid"
  }],
  "truncated": false
}
```

Неверный bbox/period — `bad_request`; превышение server maximum не приводит к unbounded
query, а возвращает `truncated=true`.

### 5.2. Сущность, источники и медиа

| Endpoint | Data |
| --- | --- |
| `GET /api/v1/entities/{entity_id}` | `EntityDetails` |
| `GET /api/v1/entities/{entity_id}/sources?limit&offset` | `Page[Source]` |
| `GET /api/v1/entities/{entity_id}/media?limit&offset` | `Page[PublishedMedia]` |
| `GET /api/v1/relations/{relation_id}/sources?limit&offset` | `Page[Source]` |

`EntityDetails` содержит `id`, `type`, `slug`, `title`, localized short/full description,
coordinates, period, cover URL, counts и `status=published`.

`Source` содержит `id`, `title`, `type`, author, publisher, publication year, URL,
archive reference, description и verification status. Устное свидетельство всегда имеет
`type=oral_testimony` и не маскируется под установленный факт.

`PublishedMedia` содержит безопасные public/preview URL, фактический MIME, dimensions,
caption, author, approximate date и source description. Внутренний storage key не выдаётся.

### 5.3. Граф

`GET /api/v1/entities/{entity_id}/graph`

```text
depth=1..2 (default 1)
types=EntityType[]
limit=1..40 (default 20)
period_from=integer
period_to=integer
```

```json
{
  "center": { "id": "center-uuid", "type": "settlement", "title": { "ru": "Ножай-Юрт", "ce": null } },
  "nodes": [{ "id": "person-uuid", "type": "person", "title": { "ru": "Имя", "ce": null }, "relations_count": 6 }],
  "edges": [{
    "id": "relation-uuid",
    "source_id": "person-uuid",
    "target_id": "center-uuid",
    "type": "born_in",
    "title": { "ru": "родился в", "ce": null },
    "description": { "ru": "Описание связи", "ce": null },
    "sources_count": 2
  }],
  "hidden_nodes_count": 14
}
```

Каждый edge ссылается на center или существующий node. Ответ не содержит дублей. Циклы
разрешены; self relation запрещён business rule.

### 5.4. Поиск

`GET /api/v1/search?q&types&district_id&period_from&period_to&limit&offset`

- `q`: trimmed 2–100 символов;
- `limit`: 1–50, default 20;
- `offset`: 0–1000;
- ответ: `Page[SearchItem]` с title/subtitle, cover, coordinates и relations count;
- поиск учитывает RU/CE, альтернативные и исторические названия, регистр и опечатки;
- пустой результат — 200 с `items:[]`.

### 5.5. Справочники фильтров

`GET /api/v1/catalog/options` возвращает:

```text
CatalogOptions = {
  districts: { id: UUID, title: LocalizedText }[],
  periods: { id: string, title: LocalizedText, period_from: integer | null,
             period_to: integer | null }[],
  entity_types: EntityType[]
}
```

Ответ versioned через `ETag`; frontend не придумывает district IDs и границы периодов.

## 6. Публичные заявки

Публичный автор может работать только со своим draft capability. UUID заявки не является
секретом и сам по себе не авторизует mutation. Capability хранится в Secure HttpOnly cookie
или эквивалентной server-side session; frontend его не читает и не сохраняет.

### 6.1. Endpoints

| Endpoint | Auth/ownership | Успех |
| --- | --- | --- |
| `POST /api/v1/submissions` | public + rate limit | 201 `SubmissionDraft` |
| `PATCH /api/v1/submissions/{id}` | owner, status=draft или needs_revision | 200 `SubmissionDraft` |
| `POST /api/v1/submissions/{id}/submit` | draft owner | 200 `SubmissionStatusView` |
| `POST /api/v1/submissions/status` | tracking capability в JSON body + rate limit | 200 `SubmissionStatusView` |
| `POST /api/v1/submissions/{id}/media` | owner, draft или needs_revision | 201 `SubmissionMedia` |
| `GET /api/v1/submissions/{id}/media` | draft owner/admin role | 200 list |
| `PATCH /api/v1/submissions/{id}/media/{media_id}` | owner, draft или needs_revision | 200 media |
| `DELETE /api/v1/submissions/{id}/media/{media_id}` | owner, draft или needs_revision | 200 null |

Create request:

```json
{
  "type": "new_entity",
  "related_entity_id": null,
  "settlement_id": "settlement-uuid",
  "title": "История населённого пункта",
  "description": "Описание материала",
  "source_description": "Семейный архив",
  "author_name": "Имя автора",
  "contact": "example@example.com",
  "consent": true
}
```

Response содержит UUID, случайный неугадываемый `tracking_code`, status и timestamps.
Status endpoint не возвращает contact, consent, внутренний audit и закрытые комментарии.
Он принимает `{ "tracking_code": "..." }`, отвечает с `Cache-Control: no-store` и не пишет
код в access/application logs. POST здесь является read-only и безопасен для ручного повтора.

Submit атомарно проверяет обязательные поля/consent/media metadata и меняет `draft→pending`
или `needs_revision→pending`.
Повторный submit возвращает прежний результат или `conflict`, но не дублирует событие.

### 6.2. Media upload

Multipart fields: `file`, `caption`, `author`, `approximate_date`, `source_description`,
`related_entity_id`.

Upload требует header `Idempotency-Key: <UUID>`. Frontend создаёт один key при выборе файла и
повторно использует его для retry этого файла. Одинаковый key и payload возвращают прежний
`SubmissionMedia`; другой payload с тем же key возвращает `idempotency_conflict`.

MVP принимает JPEG, PNG и WebP после проверки сигнатуры и декодирования. Настраиваемые
server limits имеют обязательные production defaults: до 10 файлов на заявку, до 10 MiB на
файл и до 40 megapixels. Сервер генерирует storage name, удаляет EXIF, создаёт WebP preview
и не публикует оригинал до решения модератора. Частично записанный файл удаляется при
ошибке; orphan draft media очищается отдельной bounded maintenance operation.

## 7. Admin API: модерация и каталог

Все endpoints требуют `moderator`, `editor` или `admin` в соответствии с permission policy.
Queue и details доступны moderator; публикация требует `moderation:publish`.

| Endpoint | Успех |
| --- | --- |
| `GET /api/v1/admin/submissions?status&type&settlement_id&created_from&created_to&limit&offset` | bounded page |
| `GET /api/v1/admin/submissions/{id}` | полная заявка с media и контактами |
| `POST /api/v1/admin/submissions/{id}/claim` | `pending→in_review` |
| `POST /api/v1/admin/submissions/{id}/publish` | атомарный `PublishResult` |
| `POST /api/v1/admin/submissions/{id}/reject` | `in_review→rejected` |
| `POST /api/v1/admin/submissions/{id}/request-revision` | `in_review→needs_revision` |

Publish request:

```json
{
  "expected_version": 3,
  "idempotency_key": "client-generated-uuid",
  "action": "create_entity",
  "payload": {
    "entity": {
      "type": "person",
      "slug": "person-name",
      "title": { "ru": "Имя личности", "ce": null },
      "short_description": { "ru": "Краткое описание", "ce": null },
      "full_description": { "ru": "Полное описание", "ce": null },
      "coordinates": null,
      "period_from": null,
      "period_to": null
    },
    "relations": [],
    "sources": [],
    "approved_media_ids": []
  },
  "comment": "Материал проверен"
}
```

`action` — discriminator, а `payload` — соответствующая Pydantic discriminated union:

| SubmissionType | PublishAction | Payload |
| --- | --- | --- |
| `new_entity` | `create_entity` | `entity`, `relations[]`, `sources[]`, `approved_media_ids[]` |
| `update_entity` | `update_entity` | `entity_id`, `entity_patch`, `sources[]`, `approved_media_ids[]` |
| `new_relation` | `create_relation` | `relation`, `sources[]` |
| `new_source` | `add_source` | `target_type`, `target_id`, `source` |
| `new_media` | `publish_media` | `target_entity_id`, `approved_media_ids[]` |
| `report_error` | `resolve_report` | `resolution`, optional `entity_patch` или `archive_entity_id` |

Несовпадение `submission.type` и `action` возвращает `invalid_transition`. Поля каждого
payload полностью задаются Pydantic/OpenAPI; неизвестные поля запрещены.

Publish выполняется в одном Unit of Work: проверяет version, роль, источники, связи и media;
создаёт/обновляет каталог; фиксирует audit; переводит заявку в `published`; делает один
commit. Ошибка откатывает всё. Повтор с тем же idempotency key возвращает тот же результат;
другой payload с тем же key — `idempotency_conflict`.

Reject/request revision принимают `{expected_version, comment}`. Пустой comment запрещён.
Конкурентное решение по устаревшей версии возвращает `conflict`.

### 7.1. Управление каталогом из `/admin`

`editor` и `admin` могут читать и изменять каталог; `moderator` имеет только read-доступ,
необходимый для заявки. DELETE означает archive, физического удаления нет.

| Endpoint | Permission | Результат |
| --- | --- | --- |
| `GET /api/v1/admin/catalog/entities?query&type&status&limit&offset` | catalog:read | `Page[AdminEntity]` |
| `POST /api/v1/admin/catalog/entities` | catalog:write | 201 `AdminEntity` |
| `PATCH /api/v1/admin/catalog/entities/{id}` | catalog:write | 200 `AdminEntity` |
| `DELETE /api/v1/admin/catalog/entities/{id}` | catalog:write | 200 null, archive |
| `GET /api/v1/admin/catalog/relations?entity_id&type&limit&offset` | catalog:read | bounded page |
| `POST /api/v1/admin/catalog/relations` | catalog:write | 201 relation |
| `PATCH /api/v1/admin/catalog/relations/{id}` | catalog:write | 200 relation |
| `DELETE /api/v1/admin/catalog/relations/{id}` | catalog:write | 200 null, archive |
| `GET /api/v1/admin/catalog/sources?query&type&limit&offset` | catalog:read | bounded page |
| `POST /api/v1/admin/catalog/sources` | catalog:write | 201 source |
| `PATCH /api/v1/admin/catalog/sources/{id}` | catalog:write | 200 source |
| `DELETE /api/v1/admin/catalog/sources/{id}` | catalog:write | 200 null, archive |
| `GET /api/v1/admin/audit?actor_id&action&created_from&created_to&limit&offset` | audit:read | bounded page |

Каждая mutation принимает `expected_version`, выполняет один UoW commit и создаёт audit
record. Source invariants применяются так же строго, как при moderation publish.

### 7.2. Экспорт каталога

`GET /api/v1/admin/catalog/export?format=json|csv&status=published|all`

- permission: `catalog:export` (`editor` и `admin`);
- streaming response с `Content-Disposition: attachment`;
- hard limits: 10 000 записей и 100 MiB; превышение — `export_too_large`;
- экспорт содержит entities, localized names, relations, sources и public media metadata;
- allowlist исключает passwords/hashes, sessions, contacts, submissions, internal storage keys
  и audit internals;
- export response — файл, поэтому не оборачивается в JSON `ApiResponse`.

## 8. Health

Health endpoints остаются platform-level и не версионируются:

| Endpoint | Назначение |
| --- | --- |
| `GET /api/health/live` | процесс жив; без внешних I/O |
| `GET /api/health/ready` | bounded probes PostgreSQL, Redis и RabbitMQ из текущей платформы |

Они используют `ApiResponse`. Наличие Redis/RabbitMQ в readiness не разрешает новым
feature-срезам использовать их без конкретного требования.

## 9. Frontend integration

- Все calls same-origin; browser прикладывает cookie автоматически.
- TanStack Query хранит server state; mutation не ретраится автоматически.
- React Hook Form + Zod дают быстрый format feedback; backend остаётся авторитетом.
- 401 от `me` — anonymous state без глобального toast.
- Protected route ждёт initial `me` и проверяет roles из backend response.
- Redirect после login допускает только validated same-origin path.
- Tracking/draft capability не попадает в localStorage/sessionStorage/IndexedDB.
- Upload показывает индивидуальный progress/error/retry без повторной отправки успешных файлов.
- Retry одного upload повторно использует его `Idempotency-Key`.
- Unknown enum/error имеет безопасный fallback.

## 10. Обязательные сценарии контракта

1. Map bbox/graph/search возвращают bounded published data и корректную пустую выдачу.
2. Сущность и связь без источника не публикуются.
3. Чужой draft UUID не позволяет читать или менять заявку и media.
4. Submit и publish идемпотентны в рамках описанного контракта.
5. Устаревшая moderation version не перезаписывает чужое решение.
6. Publish либо создаёт весь публичный результат и audit, либо ничего.
7. Invalid/oversized media не сохраняется и не публикуется.
8. Anonymous/admin role boundaries доказаны backend-тестом в обход UI.
9. Frontend проходит map→graph→source, submission и moderation critical flows.
10. OpenAPI и generated TypeScript client не имеют расхождений.
11. Editor управляет каталогом и скачивает allowlisted bounded export через `/admin`.
12. Bootstrap secret создаёт admin один раз и отсутствует в runtime logs/responses.

## 11. Явно открытые решения

- email verification, password reset и email provider;
- UI назначения ролей;
- срок хранения отклонённых заявок, контактов и оригинальных media;
- точный offline tile provider и лицензия;
- S3/MinIO migration и media antivirus pipeline;
- native mobile auth и сторонние OAuth/OIDC providers.

Эти решения не реализуются скрыто. Они сначала добавляются в ТЗ и контракт с новыми
acceptance scenarios.
