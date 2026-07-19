"""User-facing cleanup for research notes retained in catalog records."""

_PRIVATE_MARKERS = (
    "Внешний идентификатор Wikidata:",
    "Wikidata:",
    "URL записи источника:",
    "Источник координат:",
    "Статус исследования:",
)


def public_description(value: str, *, fallback: str = "Описание уточняется.") -> str:
    paragraphs = [part.strip() for part in value.split("\n\n")]
    visible = [
        paragraph
        for paragraph in paragraphs
        if paragraph and not paragraph.startswith(_PRIVATE_MARKERS)
    ]
    return "\n\n".join(visible) or fallback
