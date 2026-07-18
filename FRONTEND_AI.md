# Frontend AI: план реализации «Паутины истории Чечни»

Статус: обязательный execution brief для Frontend AI и frontend-субагентов.

Входы: `TZ.md`, `docs/api-contracts.md`, OpenAPI, локальные Claude/Codex rules и skills.

## 1. Цель и границы

Frontend должен дать посетителю понятный путь карта → граф → карточка → источник, безопасный
поток публичной заявки, рабочее место модератора и устойчивый museum mode.

Frontend не дублирует backend types/rules, не считает скрытый UI авторизацией и не хранит
server state в глобальном store. Текущий showcase заменяется вертикальными slices, а не
переписывается целиком одним агентом.

## 2. Обязательные правила каждого агента

Перед действием агент полностью читает применимые локальные rules/skills, существующий код,
тесты, generated client и Git diff.

- App отвечает за composition; business ownership — `src/modules/<domain>`.
- Другой модуль импортируется только через его public `index.ts`; deep imports запрещены.
- Generated OpenAPI client оборачивается adapter-ом владельца; manual response interfaces нет.
- TanStack Query хранит server state; React Hook Form + Zod — form/format state.
- Local UI state остаётся локальным. Zustand разрешён только для доказанно сложной graph/map
  session state и не хранит API data, account или auth token.
- Business logic запрещена в JSX, effects и generic helpers. Derived state считается при render.
- Нет `any`, `@ts-ignore`, giant context, hidden global dependency и automatic mutation retry.
- Component hard limit 300 строк; файл целится в <300, hard limit 600; функция <40/80.
- Mobile-first от 360 px; museum kiosk отдельно проверяется на 1920×1080.
- Touch target ≥44 px mobile и ≥56 px kiosk; semantic HTML, labels, keyboard focus,
  reduced motion и useful loading/error/empty/offline states обязательны.
- Тестируется цельный user interaction, а не каждый простой компонент отдельно.
- Нельзя ослаблять type/lint/boundary/test/a11y gates ради прохождения.

Любое изменение транспорта начинается с `docs/api-contracts.md`, затем OpenAPI regeneration.
Frontend не придумывает fields, enum, permissions, errors и pagination.

## 3. Модульная структура

```text
frontend/src/
├── app/                 # providers, router, layout, composition
├── modules/
│   ├── auth/            # session restore, login/logout, protected roles
│   ├── exploration/     # map, graph, search, filters, exploration session
│   ├── entities/        # details, sources, gallery, relation details
│   ├── submissions/     # public wizard, uploads, submit, tracking status
│   ├── moderation/      # queue, review, publish/reject/revision
│   ├── admin-catalog/   # catalog CRUD/archive, audit and export
│   └── kiosk/           # inactivity reset, fullscreen/offline shell
└── shared/              # domain-neutral UI, generated transport, primitives
```

`exploration` владеет совместной пользовательской сессией map/graph/search, чтобы не создавать
циклические зависимости между тремя искусственными модулями. `entities` предоставляет только
минимальный public UI/API contract. `kiosk` управляет session lifecycle, но не знает domain data.

## 4. UX и состояние

### 4.1. Главный поток

```text
Start → карта/поиск → выбранная сущность → ближайший граф → карточка/источник → назад
```

- карта остаётся основной spatial context;
- graph показывает 20 узлов по умолчанию и максимум 40;
- «Показать ещё N» явно сообщает о скрытых узлах;
- цвет всегда дополнен иконкой/текстом;
- canvas/WebGL карта и граф имеют доступную текстовую альтернативу списком;
- back возвращает ожидаемый центр, zoom, filters и раскрытый path текущего сеанса.

### 4.2. Server и local state

TanStack Query keys принадлежат модулям и включают нормализованные filters/bbox. Map movement
debounced/cancelled; устаревший ответ не перезаписывает новый viewport. Details/sources/media
загружаются по требованию и имеют bounded caching.

Допустимый local state: selected entity, viewport, active filters, expanded graph IDs, drawer,
wizard step и upload progress. Account, catalog responses и submission status — server state.

### 4.3. Museum mode

- fullscreen shell не полагается на browser fullscreen API для основной навигации;
- inactivity warning через 30 секунд, reset ещё через 10;
- reset очищает только visitor UI/session state, не QueryClient целиком и не auth модератора;
- при offline read-only dataset продолжает работать;
- submit/admin действия disabled с понятным сообщением и retry после reconnect;
- все animations уважают `prefers-reduced-motion`.

### 4.4. Submission

Один wizard: тип → объект → материал/источник → контакты/consent → фотографии → review/submit.
Draft capability остаётся HttpOnly и не читается JS. Frontend хранит только возвращённые
public IDs/status в памяти текущего workflow; tracking code показывается пользователю после
submit и не логируется analytics.

Каждый upload имеет отдельный progress, error и retry. При выборе файла frontend создаёт
`Idempotency-Key` и повторно использует его при retry, поэтому потерянный response не создаёт
дубликат. Повтор не перезагружает успешные файлы. Перед upload UI проверяет format/size для
быстрой обратной связи, но backend остаётся авторитетом.

### 4.5. Moderation

Protected route сначала восстанавливает session, затем проверяет backend roles. Queue filters
отражаются в URL. Review screen показывает источник, автора, media metadata и public preview.
Publish отправляет `expected_version` и новый idempotency key; после success инвалидирует
queue, submission details и затронутый catalog. Conflict показывает безопасное предложение
обновить заявку, не перетирая решение другого модератора.

### 4.6. Admin catalog

Frontend routes: `/admin/login`, `/admin`, `/admin/catalog/entities`,
`/admin/catalog/relations`, `/admin/catalog/sources`, `/admin/submissions`, `/admin/audit`.

`editor` и `admin` могут искать, фильтровать, создавать, редактировать и архивировать каталог.
`moderator` видит только необходимые read views. Формы используют generated types, React Hook
Form/Zod и `expected_version`. Export action скачивает JSON/CSV как файл, показывает ошибку
лимита и не пытается разобрать file response как `ApiResponse`.
Frontend никогда не читает `ADMIN_BOOTSTRAP_*` и не содержит `VITE_*` credentials: login form
передаёт введённые данные backend, а browser получает только Secure HttpOnly session cookie.

## 5. Работа Frontend Lead и субагентов

Frontend Lead владеет information architecture, design-system source, router/app composition,
OpenAPI client integration и финальным gate.

| Роль | Bounded ownership | Не трогает |
| --- | --- | --- |
| Exploration Agent | `modules/exploration/**` | auth/submission/moderation internals |
| Entity UI Agent | `modules/entities/**` | generated transport и map engine internals |
| Submission Agent | `modules/submissions/**` | moderation/auth internals |
| Moderation Agent | `modules/moderation/**` | backend rules и чужие module internals |
| Admin Catalog Agent | `modules/admin-catalog/**` | public exploration и backend persistence |
| Kiosk Agent | `modules/kiosk/**` | catalog transport и admin business rules |
| Design/A11y Reviewer | read-only visual, responsive, touch, keyboard, contrast review | implementation writes |
| Frontend QA Reviewer | read-only workflow/boundary/performance test-gap review | implementation writes |

Один writing owner на файл. Shared UI, app router, generated schema и dependencies интегрирует
Frontend Lead последовательно. Агентский handoff: outcome, changed paths, acceptance evidence,
validation, risks, next integration action.

## 6. Вертикальные slices

Номер frontend slice совпадает с backend slice. Slice не считается готовым без реального API
или deterministic contract-level fixture, которую удаляют при интеграции.
Один slice — одна исполняемая пачка/спринт; задачи, slice gate и общий frontend gate закрываются
вместе.

### 6.1. Как вести чек-лист

- `[ ]` — задача не подтверждена; `[x]` ставится только после review и evidence.
- Перед пачкой Lead записывает: `status`, `owner`, `branch/worktree`, `owned paths`, `subagents`.
- Допустимые статусы: `ready`, `running`, `review`, `blocked`, `done`.
- Один writing owner на файл; app router, design tokens, generated schema и lockfile меняет Lead.
- Frontend slice закрывается вместе с соответствующим backend contract/runtime slice.
- Следующий slice не начинается, пока batch gate текущего не завершён.

Карточка пачки:

```text
Status: ready
Owner:
Branch/worktree:
Owned paths:
Subagents:
Backend/OpenAPI dependency:
Acceptance evidence:
Skipped checks / blockers:
```

### 6.2. Обязательный frontend gate после каждой пачки

- [ ] OpenAPI regenerated; manual duplicate response types отсутствуют.
- [ ] Добавлены behavior tests для happy/loading/empty/error/authorization состояний по смыслу.
- [ ] Проверены module public APIs и отсутствие deep imports.
- [ ] Проверены 360/390/768/1280/1440; для kiosk-функций также 1920×1080.
- [ ] Проверены keyboard/focus/labels/touch targets/reduced motion.
- [ ] Проверены stale requests, cache invalidation и отсутствие automatic mutation retry.
- [ ] Выполнены команды frontend gate ниже.
- [ ] Read-only reviewer закрыл visual/a11y/test-gap замечания.
- [ ] Lead записал evidence и только после этого отметил slice как `done`.

```bash
cd frontend
npm ci
npm run format:check
npm run lint
npm run typecheck
npm run boundaries
npm run test:run
npm run build
```

### Slice 0 — foundation и contracts

- [ ] Настроить router/providers и module boundary checks поверх текущего приложения.
- [ ] Сгенерировать client для `/api/v1` и создать module adapters.
- [ ] Реализовать auth compatibility, session restore, protected roles и error mapping.
- [ ] Добавить `/admin/login` и protected `/admin/*` shell без credentials в frontend ENV.
- [ ] Зафиксировать design tokens, typography, focus, overlay и responsive shell.
- [ ] Реализовать единые loading/error/empty/offline patterns.
- [ ] Удалить transport mocks/interfaces, дублирующие generated client.

Подробные задачи Slice 0:

| ID | Владелец и owned paths | Точный результат | Обязательные сценарии/evidence |
| --- | --- | --- | --- |
| FE-0.1 | Frontend Lead: `src/app/**`, router/provider setup | App composition содержит QueryClient/router/error boundary; public и `/admin/*` layouts разделены без дублирования providers | Direct URL/reload, unknown route, provider error, route inventory и boundary check |
| FE-0.2 | API Integration Agent: generated schema + `shared/api` transport | OpenAPI generation воспроизводима; low-level client умеет JSON envelope, file response, request-id и cancellation | Clean regeneration diff, JSON/file/error parsing, abort signal, manual response interfaces отсутствуют |
| FE-0.3 | Auth Agent: `modules/auth/**` | Session restore/login/logout и role policy работают через HttpOnly cookie; return URL same-origin; 401 — anonymous | Anonymous, valid/expired session, invalid login, logout, forbidden role, external redirect rejected |
| FE-0.4 | Admin Shell Agent: app routes + minimal admin layout | `/admin/login` публичен, `/admin/*` ждёт `me`, показывает role-aware navigation и не читает bootstrap ENV | Reload protected route, pending auth state, 401/403, keyboard navigation, credentials отсутствуют в bundle/storage |
| FE-0.5 | Design System Agent: `shared/ui`, tokens/styles | Один набор tokens/primitives покрывает typography, spacing, focus, overlay, 44/56px targets и reduced motion | Story/test page на agreed viewports, focus/contrast evidence, components не содержат domain logic |
| FE-0.6 | UX State Agent: shared patterns только если domain-neutral | Loading/empty/error/offline компоненты имеют понятный title/action/live status и безопасный unknown-error fallback | Slow/empty/known/unknown/offline states, retry не дублирует mutation, screen-reader announcement |

Gate Slice 0:

- [ ] Anonymous/authenticated/forbidden/admin routing scenarios проходят.
- [ ] 401 от `me` обрабатывается как anonymous state без global error.
- [ ] Redirect после login допускает только same-origin path.
- [ ] `ADMIN_BOOTSTRAP_*` и auth token отсутствуют в bundle/storage.
- [ ] Typecheck, lint, boundaries, auth tests, build и shell a11y зелёные.

### Slice 1 — map и entity

- [ ] Подключить MapLibre style, Chechnya bounds, zoom/pan и clustering.
- [ ] Реализовать bounded bbox requests, filters и marker selection.
- [ ] Получать district IDs/periods/types только из catalog options API.
- [ ] Реализовать entity drawer/page, sources и media gallery.
- [ ] Отменять stale viewport queries и не дублировать markers.
- [ ] Добавить mouse/touch/keyboard navigation и accessible list alternative.
- [ ] Сохранить ожидаемый viewport/filter state при возврате.

Подробные задачи Slice 1:

| ID | Владелец и owned paths | Точный результат | Обязательные сценарии/evidence |
| --- | --- | --- | --- |
| FE-1.1 | Exploration Agent: map adapter/components | MapLibre instance создаётся/очищается один раз, Chechnya bounds/style/clusters/markers не управляют business workflow напрямую | Mount/unmount/remount, resize, style failure, no duplicate listeners/markers, browser console clean |
| FE-1.2 | Exploration Agent: map query adapter/hooks | Normalized bbox/zoom/filters формируют stable query key; previous request abort; response truncation отображается | Rapid pan/zoom, same bbox cache, invalid filter, stale response, offline/error/retry |
| FE-1.3 | Exploration Agent: filters model/UI | District/period/type options приходят из API; URL/state serialization deterministic и reset возвращает defaults | Loading options, unknown/deleted option, combined filters, back/forward, mobile filter drawer focus |
| FE-1.4 | Entity UI Agent: `modules/entities/**` | Drawer/page показывает localized details, counts, sources и gallery через generated adapters и public module API | No source/media, long text, broken image, 404, close/back focus restore, mobile/desktop layout |
| FE-1.5 | A11y owner: map list alternative | Все видимые точки доступны как semantic list/search result; selection синхронизирована с map без color-only meaning | Keyboard-only place→entity, screen reader labels, 44/56px targets, zoom controls named |
| FE-1.6 | Frontend QA: browser workflow | Viewport/filter/selected entity корректно сохраняются при drawer/page/back без global server-state copy | Map→entity→source→back на 360/768/1440/1920, screenshot/trace evidence при visual change |

Gate Slice 1:

- [ ] Loading/empty/error/truncated map states понятны пользователю.
- [ ] Rapid pan/zoom не показывает устаревшие точки.
- [ ] Map→entity→source→back component/E2E scenario проходит.
- [ ] Все viewports и 1920×1080 touch layout проверены.
- [ ] Canvas/WebGL имеет keyboard/list alternative.

### Slice 2 — graph и search

- [ ] Отделить Cytoscape adapter от React workflow/business state.
- [ ] Реализовать center/nodes/edges, expand/collapse и hidden count.
- [ ] Реализовать path highlight, entity details и возврат к карте.
- [ ] Реализовать debounced/cancelled search, filters и opening result.
- [ ] Не создавать duplicate nodes/edges при повторном раскрытии.
- [ ] Добавить keyboard list representation и reduced-motion behavior.
- [ ] Проверить browser performance на 40 nodes.

Подробные задачи Slice 2:

| ID | Владелец и owned paths | Точный результат | Обязательные сценарии/evidence |
| --- | --- | --- | --- |
| FE-2.1 | Graph Agent: Cytoscape adapter | Imperative graph lifecycle/layout/event wiring изолированы; React получает typed domain-neutral events; cleanup полный | Remount, center change, resize, failed layout, duplicate listener/node prevention |
| FE-2.2 | Graph Agent: exploration graph model/hooks | Merge nodes/edges idempotent, center/path/expanded IDs локальны; server responses остаются Query data | Expand same node twice, cycle, hidden count, collapse, hard limit, return to prior map state |
| FE-2.3 | Graph UI Agent: controls/details | Node/edge selection, relation label/source action, «Показать ещё N» и loading/error states понятны touch/mouse | Slow next level, missing edge source, graph error recovery, selected path contrast/icons |
| FE-2.4 | Search Agent: search adapter/UI | 2–100 char query debounce+abort, filters/pagination и result actions используют one source of truth | Rapid typing, empty, typo/CE/alternative results, stale response, show more, open on map/graph |
| FE-2.5 | A11y owner: graph list representation | Эквивалентный semantic список позволяет выбрать node/relation/source без Cytoscape; focus возвращается ожидаемо | Full keyboard map→graph→source→back, screen-reader labels/live loading, reduced-motion layout |
| FE-2.6 | Performance reviewer: browser trace | 40 nodes не вызывают лишние React renders/listeners; target FPS/interaction latency измерены на target-like device | Trace/profile attached, dataset/device described, regression threshold or blocker recorded |

Gate Slice 2:

- [ ] Dedup/cycle/hidden-count и expand/collapse scenarios проходят.
- [ ] Rapid query change не показывает старый search response.
- [ ] Empty/error/limit graph states отображаются корректно.
- [ ] Map→graph→source→back E2E и keyboard flow проходят.
- [ ] Performance evidence приложен к handoff.

### Slice 3 — submissions и media

- [ ] Реализовать accessible wizard и schema по каждому `SubmissionType`.
- [ ] Реализовать create/update/submit/status adapters.
- [ ] Реализовать исправление `needs_revision` и повторный submit.
- [ ] Реализовать multiple upload progress/error/retry/edit/delete.
- [ ] Создавать один idempotency key на файл и сохранять его для retry.
- [ ] Не хранить capability/tracking/auth secrets в browser storage и analytics.
- [ ] Реализовать ownership/expired/offline/validation states.

Подробные задачи Slice 3:

| ID | Владелец и owned paths | Точный результат | Обязательные сценарии/evidence |
| --- | --- | --- | --- |
| FE-3.1 | Submission Agent: form schemas/workflow | Discriminated wizard показывает только поля выбранного SubmissionType; RHF/Zod проверяет format, backend errors маппятся к fields/form | Six types, back/forward without loss, conditional required fields, server 422/unknown error |
| FE-3.2 | Submission Agent: API adapters/query keys | Create/PATCH/submit/status используют generated types; status read-only POST не попадает в URL/cache logs | Create, partial patch/null, submit replay, invalid tracking, rate limit/Retry-After |
| FE-3.3 | Submission Agent: revision flow | `needs_revision` показывает public comment, разрешает edit existing fields/media и повторный submit | Refresh/reopen, revision edit, invalid transition, second revision, published/rejected read-only |
| FE-3.4 | Upload Agent: upload model/components | Каждый файл имеет stable client ID/idempotency key, progress, server media ID, status/error и cancel/retry | Parallel files, one fail, lost response retry, cancel, remove/edit metadata, no successful re-upload |
| FE-3.5 | Security/Privacy reviewer: browser boundaries | Cookie/capability не читаются; tracking/contact/file content не уходят в logs, URL, analytics или persistent stores | Storage/network/console inspection, reload behavior documented, preview object URLs revoked |
| FE-3.6 | A11y/Responsive owner: wizard/upload | Step headings, labels, error summary, live progress и focus transitions работают mobile/kiosk/keyboard | 360/390/768/1920, keyboard-only submit, invalid file announcement, offline reconnect |

Gate Slice 3:

- [ ] Draft→submit и needs_revision→edit→submit workflows проходят.
- [ ] Один failed upload не повторяет успешные файлы.
- [ ] Lost response retry использует прежний key и не показывает duplicate media.
- [ ] Чужой/expired draft и invalid media показывают безопасное восстановление.
- [ ] Mobile/kiosk form, focus/error summary и upload live status проверены.

### Slice 4 — moderation

- [ ] Реализовать login/role guard, queue, URL filters и bounded pagination.
- [ ] Реализовать full review, selected media и claim.
- [ ] Реализовать discriminated publish/reject/request revision forms.
- [ ] Обработать version conflict, idempotent retry и post-publish cache sync.
- [ ] Реализовать admin catalog list/create/edit/archive с generated schemas.
- [ ] Реализовать audit view и bounded JSON/CSV file export.
- [ ] Скрытие controls дополнить обязательной обработкой backend 403.

Подробные задачи Slice 4:

| ID | Владелец и owned paths | Точный результат | Обязательные сценарии/evidence |
| --- | --- | --- | --- |
| FE-4.1 | Moderation Agent: queue routes/query/UI | URL-backed status/type/date/district filters, bounded pagination и claim state не дублируются в global store | Direct filtered URL, empty/error, rapid filters, back/forward, two-tab claim conflict |
| FE-4.2 | Moderation Agent: review UI | Full submission/contact/source/media metadata и selected media доступны по permissions; unsafe content рендерится как text | Missing media/source, long/untrusted text, broken preview, unauthorized contact access |
| FE-4.3 | Moderation Agent: decision forms | Publish form выбирает discriminated action/payload по SubmissionType; reject/revision требуют comment | Six publish actions, source invariant error, invalid transition, confirmation/focus, retry same key |
| FE-4.4 | Conflict/cache owner: mutations | expected version conflict сохраняет local unsaved input и предлагает refresh; success инвалидирует точные queue/catalog keys | Concurrent publish/edit, lost response replay, rollback error, public map reflects commit only |
| FE-4.5 | Admin Catalog Agent: list/edit/archive | Entity/relation/source pages используют URL filters, RHF/Zod, expected version и audit-aware archive confirmation | Role matrix, create/edit conflict, missing source, archive/restore policy, 403 despite visible control |
| FE-4.6 | Admin Audit/Export Agent | Audit filters bounded; JSON/CSV download обрабатывает filename/content type/size/403 без попытки JSON unwrap | Empty export, both formats, size error, interrupted download, CSV safe open, no contacts/secrets |
| FE-4.7 | A11y/Responsive reviewer: admin | Tables имеют mobile alternative, headers/captions, keyboard actions; dialogs restore focus; status not color-only | 360/768/1280/1440, keyboard queue→decision, axe/manual evidence |

Gate Slice 4:

- [ ] Anonymous/forbidden/editor/moderator/admin permission scenarios проходят.
- [ ] Concurrent moderator conflict не теряет несохранённую работу.
- [ ] Publish result появляется в public map/graph после cache invalidation.
- [ ] Archive исчезает из public UI и остаётся в admin/audit.
- [ ] Export скачивается как файл; limit/error/forbidden states проверены.

### Slice 5 — museum/release readiness

- [ ] Реализовать inactivity warning/reset без очистки admin session.
- [ ] Собрать offline read-only package с versioned `chechnya.pmtiles` и media.
- [ ] Исключить runtime tile/network dependency в offline mode.
- [ ] Показывать OSM attribution и включить provenance/license manifest.
- [ ] Реализовать offline/reconnect states для submission/admin actions.
- [ ] Провести 30-minute kiosk smoke и несколько последовательных sessions.

Подробные задачи Slice 5:

| ID | Владелец и owned paths | Точный результат | Обязательные сценарии/evidence |
| --- | --- | --- | --- |
| FE-5.1 | Kiosk Agent: inactivity state machine | Activity sources bounded; warning at 30s, reset at +10s; visitor state clears, admin session/data never leaks into kiosk | Touch/mouse/keyboard activity, warning continue, timeout reset, repeated sessions, clock-driven tests without sleeps |
| FE-5.2 | Offline Agent: asset/data loading | App resolves versioned PMTiles/media/read dataset locally, detects offline and makes zero unexpected external requests | Cold/warm offline start, missing/corrupt artifact, network trace, version mismatch/recovery |
| FE-5.3 | Offline UX Agent: states | Public read flow remains usable; submission/admin clearly disabled offline and recover on reconnect without duplicate mutation | Offline during map/details/upload/admin edit, reconnect, pending user input preservation, safe retry |
| FE-5.4 | License owner: attribution UI/manifest | OSM attribution always visible in map/offline build; provenance/license manifest accessible without breaking kiosk UX | Desktop/mobile/kiosk visibility, offline manifest, no attribution hidden by drawer/fullscreen |
| FE-5.5 | QA/A11y owner: production browser gate | Production build passes critical desktop/mobile/kiosk E2E, axe/manual keyboard and 30-minute smoke | Commands/results, browser/device/version, console/network trace, screenshots only for meaningful visual evidence |
| FE-5.6 | Frontend Lead: release handoff | Bundle changes, OpenAPI version, offline artifact, known device/UX gaps and rollback instructions documented | Clean final diff, no secrets/dead styles, skipped checks assigned owner/date, integration approval |

Gate Slice 5:

- [ ] `./scripts/quality_gate.sh` полностью зелёный.
- [ ] Desktop/mobile E2E и a11y проходят на production build.
- [ ] Offline map→graph→source работает с отключённой сетью.
- [ ] 30-minute smoke, inactivity warning/reset и reconnect подтверждены evidence.
- [ ] Bundle/console/network проверены на secrets, errors и неожиданные external requests.
- [ ] Release notes содержат known UX/device gaps.

## 7. Test strategy

- Module/component: complete interaction со связанными assertions и realistic API adapter fake.
- Integration: QueryClient/router/form/upload/role wiring, cancellation и cache invalidation.
- E2E: map→graph→source; revision submission с несколькими фото; moderator publish;
  admin catalog/export; offline kiosk/reset.
- A11y: keyboard, focus order/trap/restore, labels, live status, contrast, reduced motion.
- Performance: не измерять FPS в jsdom; browser trace на target-like hardware.

Запрещены giant snapshots, sleeps, private implementation assertions и тесты каждого
тривиального UI primitive. Network waits — event/response based.

## 8. Definition of Done

- пользовательская цель и owning module ясны;
- transport взят из generated client, adapter и visible states реализованы;
- server/form/local state находятся в правильных владельцах;
- нет deep imports, `any`, ignore directives, effect-derived state и giant components;
- responsive, touch, keyboard, reduced motion, loading/error/empty/offline проверены;
- Prettier, ESLint, TypeScript, boundaries, Vitest, build, E2E и a11y проходят;
- OpenAPI/client synchronized, production bundle и browser console проверены;
- final diff не содержит секретов, dead styles, unrelated rewrites и weakened gates;
- skipped device/browser checks сообщены честно.
