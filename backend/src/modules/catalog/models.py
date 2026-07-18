from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import UserDefinedType

from common.base_model import BaseDBModel
from modules.catalog.domain import EntityType, PublicationStatus, RelationType, SourceType


class PointGeometry(UserDefinedType[Any]):
    cache_ok = True

    def get_col_spec(self, **_: object) -> str:
        return "geometry(Point,4326)"


def enum_column(enum_type: type[Any], name: str) -> Enum:
    return Enum(
        enum_type,
        name=name,
        native_enum=False,
        values_callable=lambda values: [value.value for value in values],
        create_constraint=True,
        validate_strings=True,
    )


class District(BaseDBModel):
    __tablename__ = "catalog_districts"

    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    title_ru: Mapped[str] = mapped_column(String(240), nullable=False)
    title_ce: Mapped[str | None] = mapped_column(String(240))


class Period(BaseDBModel):
    __tablename__ = "catalog_periods"
    __table_args__ = (
        CheckConstraint(
            "period_from IS NULL OR period_to IS NULL OR period_from <= period_to",
            name="ck_catalog_period_order",
        ),
        UniqueConstraint("key", name="uq_catalog_period_key"),
        Index("ix_catalog_periods_order", "display_order", "key"),
    )

    key: Mapped[str] = mapped_column(String(80), nullable=False)
    title_ru: Mapped[str] = mapped_column(String(240), nullable=False)
    title_ce: Mapped[str | None] = mapped_column(String(240))
    period_from: Mapped[int | None] = mapped_column(Integer)
    period_to: Mapped[int | None] = mapped_column(Integer)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)


class Entity(BaseDBModel):
    __tablename__ = "catalog_entities"
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_catalog_entity_version_positive"),
        CheckConstraint(
            "period_from IS NULL OR period_to IS NULL OR period_from <= period_to",
            name="ck_catalog_entity_period_order",
        ),
        Index("ix_catalog_entities_public_map", "status", "type", "district_id"),
        Index("ix_catalog_entities_coordinate_gist", "coordinate", postgresql_using="gist"),
    )

    type: Mapped[EntityType] = mapped_column(
        enum_column(EntityType, "catalog_entity_type"), nullable=False
    )
    slug: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    status: Mapped[PublicationStatus] = mapped_column(
        enum_column(PublicationStatus, "catalog_publication_status"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    coordinate: Mapped[Any | None] = mapped_column(PointGeometry())
    period_from: Mapped[int | None] = mapped_column(Integer)
    period_to: Mapped[int | None] = mapped_column(Integer)
    district_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("catalog_districts.id", ondelete="RESTRICT")
    )


class EntityText(BaseDBModel):
    __tablename__ = "catalog_entity_texts"
    __table_args__ = (
        UniqueConstraint("entity_id", "locale", name="uq_catalog_entity_text_locale"),
        CheckConstraint("locale IN ('ru', 'ce')", name="ck_catalog_entity_text_locale"),
        Index("ix_catalog_entity_text_title", "title"),
    )

    entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("catalog_entities.id", ondelete="CASCADE"), nullable=False
    )
    locale: Mapped[str] = mapped_column(String(2), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    short_description: Mapped[str] = mapped_column(Text, nullable=False)
    full_description: Mapped[str] = mapped_column(Text, nullable=False)


class EntityName(BaseDBModel):
    __tablename__ = "catalog_entity_names"
    __table_args__ = (
        UniqueConstraint("entity_id", "locale", "name", name="uq_catalog_entity_name"),
        CheckConstraint("locale IN ('ru', 'ce')", name="ck_catalog_entity_name_locale"),
        Index("ix_catalog_entity_names_name", "name"),
    )

    entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("catalog_entities.id", ondelete="CASCADE"), nullable=False
    )
    locale: Mapped[str] = mapped_column(String(2), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)


class Relation(BaseDBModel):
    __tablename__ = "catalog_relations"
    __table_args__ = (
        CheckConstraint(
            "source_entity_id <> target_entity_id",
            name="ck_catalog_relation_distinct_entities",
        ),
        CheckConstraint("version > 0", name="ck_catalog_relation_version_positive"),
        CheckConstraint(
            "period_from IS NULL OR period_to IS NULL OR period_from <= period_to",
            name="ck_catalog_relation_period_order",
        ),
        Index("ix_catalog_relations_source_status", "source_entity_id", "status"),
        Index("ix_catalog_relations_target_status", "target_entity_id", "status"),
    )

    source_entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("catalog_entities.id", ondelete="RESTRICT"), nullable=False
    )
    target_entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("catalog_entities.id", ondelete="RESTRICT"), nullable=False
    )
    type: Mapped[RelationType] = mapped_column(
        enum_column(RelationType, "catalog_relation_type"), nullable=False
    )
    title_ru: Mapped[str] = mapped_column(String(300), nullable=False)
    title_ce: Mapped[str | None] = mapped_column(String(300))
    description_ru: Mapped[str] = mapped_column(Text, nullable=False)
    description_ce: Mapped[str | None] = mapped_column(Text)
    period_from: Mapped[int | None] = mapped_column(Integer)
    period_to: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[PublicationStatus] = mapped_column(
        enum_column(PublicationStatus, "catalog_relation_status"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class Source(BaseDBModel):
    __tablename__ = "catalog_sources"
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_catalog_source_version_positive"),
        Index("ix_catalog_sources_public", "status", "is_verified"),
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    type: Mapped[SourceType] = mapped_column(
        enum_column(SourceType, "catalog_source_type"), nullable=False
    )
    author: Mapped[str | None] = mapped_column(String(300))
    publisher: Mapped[str | None] = mapped_column(String(300))
    publication_year: Mapped[int | None] = mapped_column(Integer)
    url: Mapped[str | None] = mapped_column(String(2048))
    archive_reference: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[PublicationStatus] = mapped_column(
        enum_column(PublicationStatus, "catalog_source_status"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class EntitySource(BaseDBModel):
    __tablename__ = "catalog_entity_sources"
    __table_args__ = (UniqueConstraint("entity_id", "source_id", name="uq_catalog_entity_source"),)

    entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("catalog_entities.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("catalog_sources.id", ondelete="RESTRICT"), nullable=False
    )


class RelationSource(BaseDBModel):
    __tablename__ = "catalog_relation_sources"
    __table_args__ = (
        UniqueConstraint("relation_id", "source_id", name="uq_catalog_relation_source"),
    )

    relation_id: Mapped[UUID] = mapped_column(
        ForeignKey("catalog_relations.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("catalog_sources.id", ondelete="RESTRICT"), nullable=False
    )
