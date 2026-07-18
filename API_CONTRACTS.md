# API CONTRACTS — «Паутина истории Чечни»

## 1. Общие положения

Базовый префикс:

```text
/api/v1
```

Основной формат:

```text
application/json
```

Загрузка фотографий:

```text
multipart/form-data
```

Идентификаторы:

```text
UUID
```

Дата и время:

```text
ISO 8601
```

---

# 2. Enum

## EntityType

```json
[
  "settlement",
  "person",
  "event",
  "landmark",
  "natural_object",
  "cultural_object",
  "organization",
  "university_object",
  "artifact"
]
```

## RelationType

```json
[
  "born_in",
  "lived_in",
  "worked_in",
  "studied_in",
  "taught_at",
  "participated_in",
  "located_in",
  "part_of",
  "created_by",
  "described_in",
  "connected_with",
  "connected_with_chgu"
]
```

## SubmissionType

```json
[
  "new_entity",
  "update_entity",
  "new_relation",
  "new_source",
  "new_media",
  "report_error"
]
```

## SubmissionStatus

```json
[
  "draft",
  "pending",
  "in_review",
  "needs_revision",
  "approved",
  "rejected",
  "published"
]
```

## SourceType

```json
[
  "archive_document",
  "book",
  "scientific_article",
  "museum_material",
  "official_publication",
  "photo",
  "audio",
  "video",
  "oral_testimony",
  "web_resource"
]
```

---

# 3. Общие схемы

## LocalizedText

```json
{
  "ru": "Русский текст",
  "ce": null
}
```

## Coordinates

```json
{
  "latitude": 43.092,
  "longitude": 46.378
}
```

## ErrorResponse

```json
{
  "error": {
    "code": "ENTITY_NOT_FOUND",
    "message": "Entity not found",
    "details": {}
  }
}
```

## PaginationMeta

```json
{
  "limit": 20,
  "offset": 0,
  "total": 120
}
```

---

# 4. Карта

## Получение объектов карты

```http
GET /api/v1/map/entities
```

Query:

```text
bbox
zoom
types
district_id
period_from
period_to
```

Формат bbox:

```text
min_longitude,min_latitude,max_longitude,max_latitude
```

Пример:

```http
GET /api/v1/map/entities?bbox=45.1,42.7,46.8,43.8&zoom=9&types=settlement&types=landmark
```

Response:

```json
{
  "items": [
    {
      "id": "40c73db2-cf9d-4b46-b120-842dc8e14918",
      "type": "settlement",
      "title": {
        "ru": "Ножай-Юрт",
        "ce": null
      },
      "coordinates": {
        "latitude": 43.092,
        "longitude": 46.378
      },
      "relations_count": 24,
      "cover_url": "/media/entities/nozhay-yurt.webp",
      "district_id": "fba89d6e-e029-41a7-8515-ceb70f9fe51a"
    }
  ]
}
```

---

# 5. Сущности

## Получение сущности

```http
GET /api/v1/entities/{entity_id}
```

Response:

```json
{
  "id": "40c73db2-cf9d-4b46-b120-842dc8e14918",
  "type": "settlement",
  "slug": "nozhay-yurt",
  "title": {
    "ru": "Ножай-Юрт",
    "ce": null
  },
  "short_description": {
    "ru": "Краткое описание.",
    "ce": null
  },
  "full_description": {
    "ru": "Полное описание.",
    "ce": null
  },
  "coordinates": {
    "latitude": 43.092,
    "longitude": 46.378
  },
  "period_from": null,
  "period_to": null,
  "cover_url": "/media/entities/nozhay-yurt.webp",
  "relations_count": 24,
  "sources_count": 8,
  "media_count": 6,
  "status": "published"
}
```

## Источники сущности

```http
GET /api/v1/entities/{entity_id}/sources
```

Response:

```json
{
  "items": [
    {
      "id": "3893c838-a693-4719-93a2-a0979befa0fa",
      "title": "Название источника",
      "type": "book",
      "author": "Автор",
      "publisher": "Издательство",
      "publication_year": 2020,
      "url": null,
      "archive_reference": null,
      "description": "Описание источника",
      "verification_status": "verified"
    }
  ]
}
```

## Фотографии сущности

```http
GET /api/v1/entities/{entity_id}/media
```

Response:

```json
{
  "items": [
    {
      "id": "59be1cd1-90c2-4dd7-adbe-3ffcb4c85c54",
      "url": "/media/entities/photo-1.webp",
      "preview_url": "/media/previews/photo-1.webp",
      "mime_type": "image/webp",
      "width": 1600,
      "height": 900,
      "caption": "Подпись",
      "author": "Автор фотографии",
      "approximate_date": "1985",
      "source_description": "Семейный архив",
      "status": "published"
    }
  ]
}
```

---

# 6. Паутина связей

## Получение графа

```http
GET /api/v1/entities/{entity_id}/graph
```

Query:

```text
depth
types
limit
period_from
period_to
```

Response:

```json
{
  "center": {
    "id": "40c73db2-cf9d-4b46-b120-842dc8e14918",
    "type": "settlement",
    "title": {
      "ru": "Ножай-Юрт",
      "ce": null
    },
    "cover_url": "/media/entities/nozhay-yurt.webp",
    "relations_count": 24,
    "coordinates": {
      "latitude": 43.092,
      "longitude": 46.378
    }
  },
  "nodes": [
    {
      "id": "e566f611-ec9a-4864-a7bb-fd9a85a29304",
      "type": "person",
      "title": {
        "ru": "Имя личности",
        "ce": null
      },
      "cover_url": "/media/entities/person-1.webp",
      "relations_count": 6,
      "coordinates": null
    }
  ],
  "edges": [
    {
      "id": "632f357f-c2a2-42d5-8ea0-1831145460bc",
      "source_id": "e566f611-ec9a-4864-a7bb-fd9a85a29304",
      "target_id": "40c73db2-cf9d-4b46-b120-842dc8e14918",
      "type": "born_in",
      "title": {
        "ru": "родился в",
        "ce": null
      },
      "description": {
        "ru": "Объяснение связи.",
        "ce": null
      },
      "sources_count": 2
    }
  ],
  "hidden_nodes_count": 14
}
```

## Источники связи

```http
GET /api/v1/relations/{relation_id}/sources
```

Response аналогичен источникам сущности.

---

# 7. Поиск

```http
GET /api/v1/search
```

Query:

```text
q
types
district_id
period_from
period_to
limit
offset
```

Response:

```json
{
  "items": [
    {
      "id": "40c73db2-cf9d-4b46-b120-842dc8e14918",
      "type": "settlement",
      "title": {
        "ru": "Ножай-Юрт",
        "ce": null
      },
      "subtitle": {
        "ru": "Ножай-Юртовский район",
        "ce": null
      },
      "cover_url": "/media/entities/nozhay-yurt.webp",
      "coordinates": {
        "latitude": 43.092,
        "longitude": 46.378
      },
      "relations_count": 24
    }
  ],
  "meta": {
    "limit": 20,
    "offset": 0,
    "total": 1
  }
}
```

---

# 8. Пользовательские заявки

## Создание заявки

```http
POST /api/v1/submissions
```

Request:

```json
{
  "type": "new_entity",
  "related_entity_id": null,
  "settlement_id": "40c73db2-cf9d-4b46-b120-842dc8e14918",
  "title": "История населённого пункта",
  "description": "Описание материала",
  "source_description": "Семейный архив",
  "author_name": "Имя автора",
  "contact": "example@example.com",
  "consent": true
}
```

Response:

```json
{
  "id": "253c8e89-6acd-4114-b749-046956970cb0",
  "tracking_code": "HISTORY-000001",
  "status": "draft",
  "created_at": "2026-07-18T12:00:00Z",
  "updated_at": "2026-07-18T12:00:00Z"
}
```

## Изменение черновика

```http
PATCH /api/v1/submissions/{submission_id}
```

Request:

```json
{
  "title": "Обновлённое название",
  "description": "Обновлённое описание",
  "source_description": "Архив семьи",
  "author_name": "Имя автора",
  "contact": "example@example.com"
}
```

## Отправка на модерацию

```http
POST /api/v1/submissions/{submission_id}/submit
```

Response:

```json
{
  "id": "253c8e89-6acd-4114-b749-046956970cb0",
  "tracking_code": "HISTORY-000001",
  "status": "pending",
  "submitted_at": "2026-07-18T12:30:00Z"
}
```

## Получение статуса

```http
GET /api/v1/submissions/{tracking_code}
```

Response:

```json
{
  "id": "253c8e89-6acd-4114-b749-046956970cb0",
  "tracking_code": "HISTORY-000001",
  "type": "new_entity",
  "title": "История населённого пункта",
  "status": "in_review",
  "moderator_comment": null,
  "created_at": "2026-07-18T12:00:00Z",
  "submitted_at": "2026-07-18T12:30:00Z",
  "updated_at": "2026-07-18T13:00:00Z"
}
```

---

# 9. Фотографии заявки

## Загрузка фотографии

```http
POST /api/v1/submissions/{submission_id}/media
Content-Type: multipart/form-data
```

Поля:

```text
file
caption
author
approximate_date
source_description
related_entity_id
```

Response:

```json
{
  "id": "59be1cd1-90c2-4dd7-adbe-3ffcb4c85c54",
  "submission_id": "253c8e89-6acd-4114-b749-046956970cb0",
  "original_name": "photo.jpg",
  "mime_type": "image/jpeg",
  "size_bytes": 2483821,
  "preview_url": "/media/previews/59be1cd1.webp",
  "caption": "Описание фотографии",
  "author": "Автор фотографии",
  "approximate_date": "1985",
  "source_description": "Семейный архив",
  "related_entity_id": null,
  "status": "pending"
}
```

Для нескольких фотографий frontend выполняет несколько запросов и сохраняет массив `media_id`.

## Получение фотографий заявки

```http
GET /api/v1/submissions/{submission_id}/media
```

Response:

```json
{
  "items": []
}
```

## Изменение метаданных

```http
PATCH /api/v1/submissions/{submission_id}/media/{media_id}
```

Request:

```json
{
  "caption": "Новое описание",
  "author": "Автор",
  "approximate_date": "1985",
  "source_description": "Семейный архив",
  "related_entity_id": "40c73db2-cf9d-4b46-b120-842dc8e14918"
}
```

## Удаление фотографии

```http
DELETE /api/v1/submissions/{submission_id}/media/{media_id}
```

Response:

```json
{
  "deleted": true
}
```

---

# 10. Административный пользователь

```http
GET /api/v1/admin/me
```

Response:

```json
{
  "id": "c1e4d45e-7883-47e8-aa72-671a72533433",
  "name": "Модератор",
  "email": "moderator@example.com",
  "roles": [
    "moderator"
  ]
}
```

---

# 11. Очередь модерации

```http
GET /api/v1/admin/submissions
```

Query:

```text
status
type
settlement_id
created_from
created_to
limit
offset
```

Response:

```json
{
  "items": [
    {
      "id": "253c8e89-6acd-4114-b749-046956970cb0",
      "tracking_code": "HISTORY-000001",
      "type": "new_entity",
      "title": "История населённого пункта",
      "status": "in_review",
      "settlement_id": "40c73db2-cf9d-4b46-b120-842dc8e14918",
      "media_count": 3,
      "created_at": "2026-07-18T12:00:00Z",
      "submitted_at": "2026-07-18T12:30:00Z"
    }
  ],
  "meta": {
    "limit": 20,
    "offset": 0,
    "total": 1
  }
}
```

## Полная заявка

```http
GET /api/v1/admin/submissions/{submission_id}
```

Response:

```json
{
  "id": "253c8e89-6acd-4114-b749-046956970cb0",
  "tracking_code": "HISTORY-000001",
  "type": "new_entity",
  "status": "in_review",
  "related_entity_id": null,
  "settlement_id": "40c73db2-cf9d-4b46-b120-842dc8e14918",
  "title": "История населённого пункта",
  "description": "Описание материала",
  "source_description": "Семейный архив",
  "author_name": "Имя автора",
  "contact": "example@example.com",
  "consent": true,
  "media": [],
  "created_at": "2026-07-18T12:00:00Z",
  "submitted_at": "2026-07-18T12:30:00Z",
  "updated_at": "2026-07-18T13:00:00Z"
}
```

---

# 12. Одобрение заявки

```http
POST /api/v1/admin/submissions/{submission_id}/approve
```

Request:

```json
{
  "action": "create_entity",
  "entity": {
    "type": "person",
    "slug": "person-name",
    "title": {
      "ru": "Имя личности",
      "ce": null
    },
    "short_description": {
      "ru": "Краткое описание",
      "ce": null
    },
    "full_description": {
      "ru": "Полное описание",
      "ce": null
    },
    "coordinates": null,
    "period_from": null,
    "period_to": null
  },
  "relations": [
    {
      "source_entity_id": "e566f611-ec9a-4864-a7bb-fd9a85a29304",
      "target_entity_id": "40c73db2-cf9d-4b46-b120-842dc8e14918",
      "type": "born_in",
      "title": {
        "ru": "родился в",
        "ce": null
      },
      "description": {
        "ru": "Объяснение связи",
        "ce": null
      },
      "period_from": null,
      "period_to": null
    }
  ],
  "sources": [
    {
      "title": "Название источника",
      "type": "book",
      "author": "Автор",
      "publisher": "Издательство",
      "publication_year": 2020,
      "url": null,
      "archive_reference": null,
      "description": "Описание источника"
    }
  ],
  "approved_media_ids": [
    "59be1cd1-90c2-4dd7-adbe-3ffcb4c85c54"
  ],
  "comment": "Материал проверен"
}
```

Допустимые действия:

```json
[
  "create_entity",
  "update_entity",
  "create_relation",
  "add_source",
  "publish_media"
]
```

Response:

```json
{
  "submission_id": "253c8e89-6acd-4114-b749-046956970cb0",
  "status": "published",
  "published_entity_id": "e566f611-ec9a-4864-a7bb-fd9a85a29304",
  "published_relation_ids": [
    "632f357f-c2a2-42d5-8ea0-1831145460bc"
  ],
  "published_source_ids": [
    "3893c838-a693-4719-93a2-a0979befa0fa"
  ],
  "published_media_ids": [
    "59be1cd1-90c2-4dd7-adbe-3ffcb4c85c54"
  ]
}
```

---

# 13. Отклонение

```http
POST /api/v1/admin/submissions/{submission_id}/reject
```

Request:

```json
{
  "comment": "Причина отклонения"
}
```

Response:

```json
{
  "submission_id": "253c8e89-6acd-4114-b749-046956970cb0",
  "status": "rejected",
  "moderator_comment": "Причина отклонения"
}
```

---

# 14. Запрос уточнения

```http
POST /api/v1/admin/submissions/{submission_id}/request-revision
```

Request:

```json
{
  "comment": "Нужно уточнить дату и источник фотографии"
}
```

Response:

```json
{
  "submission_id": "253c8e89-6acd-4114-b749-046956970cb0",
  "status": "needs_revision",
  "moderator_comment": "Нужно уточнить дату и источник фотографии"
}
```

---

# 15. Healthcheck

```http
GET /health
```

```json
{
  "status": "ok"
}
```

```http
GET /ready
```

```json
{
  "status": "ready",
  "database": "ok"
}
```

---

# 16. HTTP-коды

```text
200 — успешное получение или обновление
201 — успешное создание
204 — успешное удаление
400 — некорректный запрос
401 — отсутствует авторизация
403 — недостаточно прав
404 — объект не найден
409 — конфликт данных
422 — ошибка валидации
500 — внутренняя ошибка
```

---

# 17. Общая интеграционная проверка

* [ ] Создать заявку.
* [ ] Получить `submission_id`.
* [ ] Загрузить несколько фотографий.
* [ ] Изменить подписи фотографий.
* [ ] Отправить заявку.
* [ ] Получить tracking code.
* [ ] Открыть заявку в административной панели.
* [ ] Выбрать фотографии.
* [ ] Создать сущность.
* [ ] Создать связь.
* [ ] Добавить источник.
* [ ] Одобрить заявку.
* [ ] Проверить новую точку на карте.
* [ ] Проверить новый узел в паутине.
* [ ] Проверить источники.
* [ ] Проверить опубликованные фотографии.
