# Frontend sprint readiness

Актуальный срез после подключения `/api/v1` и импорта локального каталога из
`docs/test/`. Статус `done` означает завершённый пользовательский сценарий с
реальным transport adapter, а не только готовую mock-вёрстку.

Последний quality gate: Prettier, ESLint, TypeScript, module boundaries и build
прошли; Vitest — 37 файлов / 102 теста; Playwright — 36 сценариев на шести
viewport-классах, включая a11y и отсутствие horizontal overflow.

## Sprint 0A — foundation and authentication

Status: **done**

- App providers, router, error boundary, direct routes и protected admin shell готовы.
- Public и admin login/session/logout работают через backend и Secure HttpOnly cookie.
- Токены не сохраняются в localStorage/sessionStorage.
- Module boundaries, responsive states и доступные loading/error/empty states действуют.

## Sprint 1 — public exploration and entity pages

Status: **done**

- Map, search, catalog options, entity details, sources и media используют real API.
- Map остаётся видимой при loading/error/empty и имеет локальный WebGL fallback.
- Локальный demo seed содержит 1 339 опубликованных объектов; 822 имеют координаты.
- Поиск открывает canonical entity route даже для событий/личностей без координат.
- URL filters, browser Back и focus restoration сохраняются.

Открыто: versioned offline tile artifact и утверждённые реальные фото с provenance.

## Sprint 2 — graph, chronology and mobile exploration

Status: **done**

- Хронология получает опубликованные события из `/api/v1/timeline/events`.
- Query, district и period filters передаются backend; события наследуют известный район места.
- Режим «Паутина связей» строит реальный node-link graph и доступное дерево ветвей,
  без static UUID/relations.
- Graph запрашивается с `depth=2`; источники раскрываются для первого и второго уровня.
- Mobile filter drawer, keyboard/focus behavior и 360px layout готовы.

## Sprint 3 — public submissions and media

Status: **integrated with contract gaps**

- Create, versioned patch/submit, tracking status и media lifecycle используют backend.
- Same-origin draft capability остаётся только в HttpOnly cookie.
- Upload retry сохраняет idempotency key; 403/404/409/422 имеют typed UI states.

Открыто:

- backend не предоставляет bounded selector опубликованных entities/settlements;
  UI не подставляет mock UUID и разрешает продолжить без привязки;
- нет owner-safe GET draft для восстановления полной формы после reload;
- `new_relation` заблокирован до точного контракта двух концов и relation type.

## Sprint 4 — moderation and admin catalog

Status: **done for current API contract**

Готово через real API:

- admin session and role guard;
- moderation queue/detail, claim, revision request, reject;
- все шесть publication actions с expected version и idempotency;
- выбор и защищённый preview вложений модерации;
- admin entity/relation/source CRUD, archive, audit и binary export.

Открыто:

- authoritative permissions пока вычисляются из roles; backend повторно авторизует запросы;
- aggregate dashboard endpoint отсутствует, поэтому overview не показывает фиктивные метрики.

## Sprint 5 — production hardening

Status: **not done**

- Commons evidence содержит 437 реальных photo links с rights metadata; локальные
  оригиналы/превью пока не загружены как MediaAsset.
- Нужны автономные tiles, production observability/SLO, backup restore evidence и release E2E.
- Bundle splitting остаётся performance-задачей: MapLibre загружается отдельным крупным chunk.
