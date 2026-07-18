# BACKEND AI — «Паутина истории Чечни»

## 1. Назначение

Документ определяет задачи **Backend AI** и его субагентов.

Backend отвечает за:

* PostgreSQL и PostGIS;
* модели данных;
* исторические сущности;
* связи между сущностями;
* источники;
* фотографии;
* публичное API;
* поиск;
* пользовательские заявки;
* модерацию;
* административное API;
* миграции;
* seed-данные;
* backend-тестирование.

Перед началом работы Backend AI и каждый субагент обязаны прочитать и соблюдать существующие локальные правила проекта.

---

# 2. Backend-стек

```text
Python 3.12
FastAPI
PostgreSQL
PostGIS
SQLAlchemy 2.0
Alembic
asyncpg
Pydantic v2
Pytest
Docker
```

Хранение файлов:

```text
MVP: локальное файловое хранилище
Production: S3 / MinIO
```

---

# 3. Backend AI и субагенты

## Backend AI

Координирует backend-разработку:

* разбивает работу на задачи;
* назначает задачи субагентам;
* контролирует зависимости;
* проверяет результаты;
* согласовывает контракты с Frontend AI;
* обновляет OpenAPI;
* запускает итоговые проверки.

## Architecture Agent

Отвечает за:

* структуру backend;
* конфигурацию;
* общие схемы;
* формат ошибок;
* пагинацию;
* авторизацию;
* зависимости между слоями.

## Database Agent

Отвечает за:

* PostgreSQL;
* PostGIS;
* SQLAlchemy-модели;
* Alembic;
* индексы;
* ограничения;
* seed-данные;
* оптимизацию запросов.

## Public API Agent

Отвечает за:

* карту;
* сущности;
* паутину связей;
* поиск;
* источники;
* опубликованные фотографии.

## Submission Agent

Отвечает за:

* создание заявки;
* изменение черновика;
* отправку на модерацию;
* получение статуса заявки.

## Media Agent

Отвечает за:

* загрузку фотографий;
* несколько фотографий в одной заявке;
* метаданные;
* превью;
* привязку фотографий к заявкам и сущностям.

## Moderation Agent

Отвечает за:

* очередь заявок;
* просмотр заявки;
* одобрение;
* отклонение;
* запрос уточнения;
* публикацию сущностей, связей, источников и фотографий.

## Backend QA Agent

Отвечает за:

* unit-тесты;
* API-тесты;
* integration-тесты;
* тесты PostgreSQL;
* тесты миграций;
* полный регрессионный прогон.

## Infrastructure Agent

Отвечает за:

* Docker;
* переменные окружения;
* healthcheck;
* запуск миграций;
* запуск seed;
* локальный и production-запуск.

---

# 4. Доменные сущности

## Entity

Универсальная историческая сущность.

Типы:

```text
settlement
person
event
landmark
natural_object
cultural_object
organization
university_object
artifact
```

Основные поля:

```text
id
entity_type
slug
title_ru
title_ce
short_description_ru
short_description_ce
full_description_ru
full_description_ce
status
location
period_from
period_to
cover_media_id
created_at
updated_at
published_at
```

`location` хранится через PostGIS.

## Relation

Связь между двумя сущностями.

```text
id
source_entity_id
target_entity_id
relation_type
title_ru
title_ce
description_ru
description_ce
period_from
period_to
status
created_at
updated_at
```

Примеры связей:

```text
born_in
lived_in
worked_in
studied_in
taught_at
participated_in
located_in
part_of
created_by
described_in
connected_with
connected_with_chgu
```

## Source

```text
id
title
source_type
author
publisher
publication_year
url
archive_reference
description
verification_status
created_at
updated_at
```

## Media

```text
id
storage_key
original_name
mime_type
size_bytes
width
height
caption
author
approximate_date
source_description
status
created_at
updated_at
```

## Submission

Типы:

```text
new_entity
update_entity
new_relation
new_source
new_media
report_error
```

Статусы:

```text
draft
pending
in_review
needs_revision
approved
rejected
published
```

## SubmissionMedia

Связывает заявку с одной или несколькими фотографиями.

## ModerationReview

Хранит решение модератора по заявке.

---

# 5. Спринт 0 — архитектура и контракты

## Architecture Agent

* [ ] Изучить локальные правила backend.
* [ ] Зафиксировать структуру backend.
* [ ] Определить общие Pydantic-схемы.
* [ ] Определить формат ошибок.
* [ ] Определить пагинацию.
* [ ] Определить формат фильтров.
* [ ] Определить общие enum.
* [ ] Согласовать `API_CONTRACTS.md`.

## Database Agent

* [ ] Подготовить ER-модель.
* [ ] Определить таблицы.
* [ ] Определить внешние ключи.
* [ ] Определить PostGIS-поля.
* [ ] Определить индексы.
* [ ] Определить таблицы заявок.
* [ ] Определить таблицы фотографий.
* [ ] Определить таблицы модерации.

## Public API Agent

* [ ] Описать API карты.
* [ ] Описать API сущностей.
* [ ] Описать API графа.
* [ ] Описать API поиска.
* [ ] Описать API источников.
* [ ] Описать API медиа.

## Submission Agent

* [ ] Описать создание заявки.
* [ ] Описать изменение заявки.
* [ ] Описать отправку заявки.
* [ ] Описать получение статуса.

## Media Agent

* [ ] Описать multipart-загрузку.
* [ ] Описать метаданные фотографии.
* [ ] Описать несколько фото в одной заявке.

## Moderation Agent

* [ ] Описать очередь модерации.
* [ ] Описать approve.
* [ ] Описать reject.
* [ ] Описать request revision.
* [ ] Описать публикацию результата.

## Проверка спринта

* [ ] Все endpoints внесены в API-контракт.
* [ ] Request/response-схемы согласованы с frontend.
* [ ] Enum согласованы.
* [ ] Контракт загрузки фотографий согласован.
* [ ] OpenAPI генерируется.

---

# 6. Спринт 1 — каркас backend и PostgreSQL

## Infrastructure Agent

* [ ] Создать FastAPI-приложение.
* [ ] Подключить конфигурацию.
* [ ] Подключить PostgreSQL.
* [ ] Подключить asyncpg.
* [ ] Добавить `/health`.
* [ ] Добавить `/ready`.
* [ ] Подготовить Dockerfile.
* [ ] Подготовить Docker Compose.
* [ ] Подготовить `.env.example`.

## Database Agent

* [ ] Подключить SQLAlchemy 2.0.
* [ ] Подключить Alembic.
* [ ] Активировать PostGIS.
* [ ] Создать базовые модели.
* [ ] Создать начальную миграцию.
* [ ] Добавить индексы.
* [ ] Создать seed-команду.

## Backend QA Agent

* [ ] Настроить Pytest.
* [ ] Настроить тестовую PostgreSQL.
* [ ] Добавить fixture БД.
* [ ] Добавить fixture API-клиента.
* [ ] Проверить healthcheck.
* [ ] Проверить миграции.
* [ ] Проверить seed.

## Проверка спринта

* [ ] Backend запускается.
* [ ] PostgreSQL подключается.
* [ ] PostGIS доступен.
* [ ] Миграции применяются.
* [ ] Seed загружается.
* [ ] Тесты проходят.

---

# 7. Спринт 2 — сущности и карта

## Database Agent

* [ ] Добавить 8–10 населённых пунктов.
* [ ] Добавить координаты.
* [ ] Добавить 10–15 личностей.
* [ ] Добавить 5–10 достопримечательностей.
* [ ] Добавить 5–8 событий.
* [ ] Добавить источники.
* [ ] Добавить фотографии.
* [ ] Добавить пространственные индексы.

## Public API Agent

Реализовать:

```http
GET /api/v1/map/entities
GET /api/v1/entities/{entity_id}
GET /api/v1/entities/{entity_id}/sources
GET /api/v1/entities/{entity_id}/media
```

Поддержать:

```text
bbox
zoom
types
district_id
period_from
period_to
```

## Backend QA Agent

* [ ] Карта без фильтров.
* [ ] Карта с bbox.
* [ ] Фильтр по типам.
* [ ] Фильтр по району.
* [ ] Карточка сущности.
* [ ] Ответ 404.
* [ ] Источники сущности.
* [ ] Фотографии сущности.

## Проверка спринта

* [ ] Координаты соответствуют API-контракту.
* [ ] Карточки возвращают необходимые поля.
* [ ] Источники доступны.
* [ ] Фотографии доступны.
* [ ] OpenAPI обновлён.

---

# 8. Спринт 3 — паутина связей

## Database Agent

* [ ] Создать типы связей.
* [ ] Добавить 50–70 связей.
* [ ] Добавить индексы связей.
* [ ] Подготовить запрос ближайших узлов.
* [ ] Подготовить раскрытие следующего уровня.

## Public API Agent

Реализовать:

```http
GET /api/v1/entities/{entity_id}/graph
GET /api/v1/relations/{relation_id}/sources
```

Параметры:

```text
depth
types
limit
period_from
period_to
```

Ответ:

```text
center
nodes
edges
hidden_nodes_count
```

## Backend QA Agent

* [ ] Объект без связей.
* [ ] `depth=1`.
* [ ] `depth=2`.
* [ ] Ограничение `limit`.
* [ ] Фильтрация типов.
* [ ] Фильтрация периода.
* [ ] Циклические связи.
* [ ] Отсутствие дублей узлов.
* [ ] Отсутствие дублей рёбер.

## Проверка спринта

* [ ] Все edges ссылаются на существующие nodes.
* [ ] `hidden_nodes_count` рассчитывается.
* [ ] Источники связи доступны.
* [ ] Graph response соответствует контракту.

---

# 9. Спринт 4 — поиск

## Database Agent

* [ ] Добавить полнотекстовый поиск PostgreSQL.
* [ ] Добавить альтернативные названия.
* [ ] Добавить чеченские названия.
* [ ] Добавить исторические названия.
* [ ] Добавить поисковые индексы.

## Public API Agent

Реализовать:

```http
GET /api/v1/search
```

Параметры:

```text
q
types
district_id
period_from
period_to
limit
offset
```

## Backend QA Agent

* [ ] Поиск населённого пункта.
* [ ] Поиск личности.
* [ ] Поиск достопримечательности.
* [ ] Поиск альтернативного названия.
* [ ] Поиск чеченского названия.
* [ ] Пустой результат.
* [ ] Пагинация.
* [ ] Комбинированные фильтры.

---

# 10. Спринт 5 — пользовательские заявки

## Submission Agent

Реализовать:

```http
POST /api/v1/submissions
PATCH /api/v1/submissions/{submission_id}
POST /api/v1/submissions/{submission_id}/submit
GET /api/v1/submissions/{tracking_code}
```

Функции:

* [ ] создание черновика;
* [ ] изменение черновика;
* [ ] связь с существующей сущностью;
* [ ] предложение новой сущности;
* [ ] добавление описания источника;
* [ ] получение tracking code;
* [ ] отправка на модерацию;
* [ ] получение статуса.

## Database Agent

* [ ] Создать таблицы заявок.
* [ ] Создать историю статусов.
* [ ] Добавить связь с существующей сущностью.
* [ ] Добавить связь с предлагаемыми данными.

## Backend QA Agent

* [ ] Новая сущность.
* [ ] Обновление сущности.
* [ ] Новая связь.
* [ ] Новый источник.
* [ ] Изменение черновика.
* [ ] Отправка заявки.
* [ ] Получение статуса.

---

# 11. Спринт 6 — фотографии в заявках

## Media Agent

Реализовать:

```http
POST /api/v1/submissions/{submission_id}/media
GET /api/v1/submissions/{submission_id}/media
PATCH /api/v1/submissions/{submission_id}/media/{media_id}
DELETE /api/v1/submissions/{submission_id}/media/{media_id}
```

Multipart-поля:

```text
file
caption
author
approximate_date
source_description
related_entity_id
```

Функции:

* [ ] загрузка одной фотографии;
* [ ] загрузка нескольких фотографий;
* [ ] генерация preview;
* [ ] сохранение метаданных;
* [ ] редактирование метаданных;
* [ ] удаление фото;
* [ ] получение списка фото.

## Database Agent

* [ ] Создать таблицу Media.
* [ ] Создать SubmissionMedia.
* [ ] Создать EntityMedia.
* [ ] Добавить индексы.

## Backend QA Agent

* [ ] Одно фото.
* [ ] Несколько фото.
* [ ] Получение списка.
* [ ] Изменение подписи.
* [ ] Изменение автора.
* [ ] Удаление фото.
* [ ] Проверка preview URL.

## Проверка спринта

* [ ] Каждое фото получает `media_id`.
* [ ] Несколько фото связаны с одной заявкой.
* [ ] Метаданные сохраняются.
* [ ] Multipart-контракт совпадает с frontend.

---

# 12. Спринт 7 — модерация

## Moderation Agent

Реализовать:

```http
GET /api/v1/admin/submissions
GET /api/v1/admin/submissions/{submission_id}
POST /api/v1/admin/submissions/{submission_id}/approve
POST /api/v1/admin/submissions/{submission_id}/reject
POST /api/v1/admin/submissions/{submission_id}/request-revision
```

Approve поддерживает:

* [ ] создание сущности;
* [ ] обновление сущности;
* [ ] создание связи;
* [ ] добавление источника;
* [ ] выбор фотографий;
* [ ] публикацию фотографий;
* [ ] комментарий модератора.

## Database Agent

* [ ] Сохранять решение модератора.
* [ ] Создавать сущность.
* [ ] Создавать связь.
* [ ] Создавать источник.
* [ ] Привязывать фотографии.
* [ ] Обновлять статус заявки.
* [ ] Сохранять аудит.

## Backend QA Agent

* [ ] Очередь заявок.
* [ ] Фильтры очереди.
* [ ] Полная карточка заявки.
* [ ] Одобрение сущности.
* [ ] Одобрение связи.
* [ ] Одобрение источника.
* [ ] Публикация выбранных фотографий.
* [ ] Отклонение.
* [ ] Запрос уточнения.
* [ ] Появление данных в публичном API.

---

# 13. Спринт 8 — административная авторизация

## Architecture Agent

* [ ] Подключить принятую в проекте авторизацию.
* [ ] Добавить роли.
* [ ] Добавить текущего пользователя.
* [ ] Подключить авторизацию к admin endpoints.

## Backend QA Agent

* [ ] Вход.
* [ ] Текущий пользователь.
* [ ] Доступ модератора.
* [ ] Доступ администратора.
* [ ] Недоступность admin API без авторизации.

---

# 14. Спринт 9 — интеграция

## Backend AI

* [ ] Сверить реализацию с `API_CONTRACTS.md`.
* [ ] Сгенерировать актуальный OpenAPI.
* [ ] Передать OpenAPI Frontend AI.
* [ ] Запустить миграции.
* [ ] Запустить seed.
* [ ] Запустить полный набор тестов.
* [ ] Проверить Docker-сборку.
* [ ] Проверить карту.
* [ ] Проверить паутину.
* [ ] Проверить поиск.
* [ ] Проверить заявки.
* [ ] Проверить несколько фотографий.
* [ ] Проверить модерацию.
* [ ] Проверить публикацию.

## Итоговый чек-лист

* [ ] PostgreSQL используется.
* [ ] PostGIS подключён.
* [ ] Миграции работают.
* [ ] Seed работает.
* [ ] Карта работает.
* [ ] Граф работает.
* [ ] Поиск работает.
* [ ] Заявки работают.
* [ ] Фотографии работают.
* [ ] Модерация работает.
* [ ] OpenAPI актуален.
* [ ] Backend-тесты проходят.
