from uuid import uuid4

import pytest
from pydantic import TypeAdapter, ValidationError

from modules.moderation.schemas import PublishBase, PublishCommand

ID = str(uuid4())
LOCALIZED = {"ru": "Текст", "ce": None}
SOURCE = {
    "title": "Источник",
    "type": "book",
    "author": None,
    "publisher": None,
    "publication_year": None,
    "url": None,
    "archive_reference": None,
    "description": "Описание",
}
ENTITY = {
    "type": "person",
    "slug": "person",
    "title": LOCALIZED,
    "short_description": LOCALIZED,
    "full_description": LOCALIZED,
    "coordinates": None,
    "period_from": None,
    "period_to": None,
}
RELATION = {
    "source_entity_id": ID,
    "target_entity_id": str(uuid4()),
    "type": "connected_with",
    "title": LOCALIZED,
    "description": LOCALIZED,
    "period_from": None,
    "period_to": None,
}


def base(action: str, payload: dict[str, object]) -> dict[str, object]:
    return {
        "expected_version": 3,
        "idempotency_key": str(uuid4()),
        "action": action,
        "payload": payload,
        "comment": "Материал проверен",
    }


@pytest.mark.parametrize(
    "document",
    [
        base(
            "create_entity",
            {"entity": ENTITY, "relations": [], "sources": [], "approved_media_ids": []},
        ),
        base(
            "update_entity",
            {
                "entity_id": ID,
                "entity_patch": {"slug": "updated"},
                "sources": [],
                "approved_media_ids": [],
            },
        ),
        base("create_relation", {"relation": RELATION, "sources": [SOURCE]}),
        base("add_source", {"target_type": "entity", "target_id": ID, "source": SOURCE}),
        base("publish_media", {"target_entity_id": ID, "approved_media_ids": [ID]}),
        base(
            "resolve_report",
            {"resolution": "Исправлено", "entity_patch": None, "archive_entity_id": None},
        ),
    ],
)
def test_discriminated_publish_commands_accept_each_complete_payload(
    document: dict[str, object],
) -> None:
    parsed: object = TypeAdapter(PublishCommand).validate_python(document)
    assert isinstance(parsed, PublishBase)
    assert parsed.action == document["action"]


def test_publish_payload_rejects_unknown_fields_and_missing_required_sources() -> None:
    unknown = base(
        "publish_media",
        {"target_entity_id": ID, "approved_media_ids": [ID], "storage_key": "private"},
    )
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        TypeAdapter(PublishCommand).validate_python(unknown)

    missing_source = base("create_relation", {"relation": RELATION, "sources": []})
    with pytest.raises(ValidationError):
        TypeAdapter(PublishCommand).validate_python(missing_source)
