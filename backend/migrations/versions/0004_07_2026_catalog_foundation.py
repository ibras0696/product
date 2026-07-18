"""catalog foundation

Revision ID: 0004_07_2026_catalog_foundation
Revises: 0003_07_2026_slice0_foundation
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_07_2026_catalog_foundation"
down_revision: str | Sequence[str] | None = "0003_07_2026_slice0_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PUBLICATION_STATUSES = ("draft", "published", "archived")
ENTITY_TYPES = (
    "settlement",
    "person",
    "event",
    "landmark",
    "natural_object",
    "cultural_object",
    "organization",
    "university_object",
    "artifact",
)
RELATION_TYPES = (
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
    "connected_with_chgu",
)
SOURCE_TYPES = (
    "archive_document",
    "book",
    "scientific_article",
    "museum_material",
    "official_publication",
    "photo",
    "audio",
    "video",
    "oral_testimony",
    "web_resource",
)


class PointGeometry(sa.types.UserDefinedType[object]):
    cache_ok = True

    def get_col_spec(self, **_: object) -> str:
        return "geometry(Point,4326)"


def base_columns() -> tuple[sa.Column[object], ...]:
    return (
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def value_enum(name: str, values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True)


def create_districts() -> None:
    op.create_table(
        "catalog_districts",
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("title_ru", sa.String(length=240), nullable=False),
        sa.Column("title_ce", sa.String(length=240), nullable=True),
        *base_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_catalog_districts"),
        sa.UniqueConstraint("slug", name="uq_catalog_districts_slug"),
    )


def create_entities() -> None:
    op.create_table(
        "catalog_entities",
        sa.Column("type", value_enum("catalog_entity_type", ENTITY_TYPES), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column(
            "status",
            value_enum("catalog_publication_status", PUBLICATION_STATUSES),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("coordinate", PointGeometry(), nullable=True),
        sa.Column("period_from", sa.Integer(), nullable=True),
        sa.Column("period_to", sa.Integer(), nullable=True),
        sa.Column("district_id", postgresql.UUID(as_uuid=True), nullable=True),
        *base_columns(),
        sa.CheckConstraint("version > 0", name="ck_catalog_entity_version_positive"),
        sa.CheckConstraint(
            "period_from IS NULL OR period_to IS NULL OR period_from <= period_to",
            name="ck_catalog_entity_period_order",
        ),
        sa.ForeignKeyConstraint(
            ["district_id"],
            ["catalog_districts.id"],
            name="fk_catalog_entities_district_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_catalog_entities"),
        sa.UniqueConstraint("slug", name="uq_catalog_entities_slug"),
    )
    op.create_index(
        "ix_catalog_entities_public_map",
        "catalog_entities",
        ["status", "type", "district_id"],
    )
    op.create_index(
        "ix_catalog_entities_coordinate_gist",
        "catalog_entities",
        ["coordinate"],
        postgresql_using="gist",
    )


def create_entity_texts() -> None:
    op.create_table(
        "catalog_entity_texts",
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("locale", sa.String(length=2), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("short_description", sa.Text(), nullable=False),
        sa.Column("full_description", sa.Text(), nullable=False),
        *base_columns(),
        sa.CheckConstraint("locale IN ('ru', 'ce')", name="ck_catalog_entity_text_locale"),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["catalog_entities.id"],
            name="fk_catalog_entity_texts_entity_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_catalog_entity_texts"),
        sa.UniqueConstraint("entity_id", "locale", name="uq_catalog_entity_text_locale"),
    )
    op.create_index("ix_catalog_entity_text_title", "catalog_entity_texts", ["title"])


def create_entity_names() -> None:
    op.create_table(
        "catalog_entity_names",
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("locale", sa.String(length=2), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        *base_columns(),
        sa.CheckConstraint("locale IN ('ru', 'ce')", name="ck_catalog_entity_name_locale"),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["catalog_entities.id"],
            name="fk_catalog_entity_names_entity_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_catalog_entity_names"),
        sa.UniqueConstraint("entity_id", "locale", "name", name="uq_catalog_entity_name"),
    )
    op.create_index("ix_catalog_entity_names_name", "catalog_entity_names", ["name"])


def create_relations() -> None:
    op.create_table(
        "catalog_relations",
        sa.Column("source_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", value_enum("catalog_relation_type", RELATION_TYPES), nullable=False),
        sa.Column("title_ru", sa.String(length=300), nullable=False),
        sa.Column("title_ce", sa.String(length=300), nullable=True),
        sa.Column("description_ru", sa.Text(), nullable=False),
        sa.Column("description_ce", sa.Text(), nullable=True),
        sa.Column("period_from", sa.Integer(), nullable=True),
        sa.Column("period_to", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            value_enum("catalog_relation_status", PUBLICATION_STATUSES),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        *base_columns(),
        sa.CheckConstraint(
            "source_entity_id <> target_entity_id",
            name="ck_catalog_relation_distinct_entities",
        ),
        sa.CheckConstraint("version > 0", name="ck_catalog_relation_version_positive"),
        sa.CheckConstraint(
            "period_from IS NULL OR period_to IS NULL OR period_from <= period_to",
            name="ck_catalog_relation_period_order",
        ),
        sa.ForeignKeyConstraint(
            ["source_entity_id"],
            ["catalog_entities.id"],
            name="fk_catalog_relations_source_entity_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_entity_id"],
            ["catalog_entities.id"],
            name="fk_catalog_relations_target_entity_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_catalog_relations"),
    )
    op.create_index(
        "ix_catalog_relations_source_status",
        "catalog_relations",
        ["source_entity_id", "status"],
    )
    op.create_index(
        "ix_catalog_relations_target_status",
        "catalog_relations",
        ["target_entity_id", "status"],
    )


def create_sources() -> None:
    op.create_table(
        "catalog_sources",
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("type", value_enum("catalog_source_type", SOURCE_TYPES), nullable=False),
        sa.Column("author", sa.String(length=300), nullable=True),
        sa.Column("publisher", sa.String(length=300), nullable=True),
        sa.Column("publication_year", sa.Integer(), nullable=True),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column("archive_reference", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column(
            "status",
            value_enum("catalog_source_status", PUBLICATION_STATUSES),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        *base_columns(),
        sa.CheckConstraint("version > 0", name="ck_catalog_source_version_positive"),
        sa.PrimaryKeyConstraint("id", name="pk_catalog_sources"),
    )
    op.create_index("ix_catalog_sources_public", "catalog_sources", ["status", "is_verified"])


def create_source_links() -> None:
    op.create_table(
        "catalog_entity_sources",
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        *base_columns(),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["catalog_entities.id"],
            name="fk_catalog_entity_sources_entity_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["catalog_sources.id"],
            name="fk_catalog_entity_sources_source_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_catalog_entity_sources"),
        sa.UniqueConstraint("entity_id", "source_id", name="uq_catalog_entity_source"),
    )
    op.create_table(
        "catalog_relation_sources",
        sa.Column("relation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        *base_columns(),
        sa.ForeignKeyConstraint(
            ["relation_id"],
            ["catalog_relations.id"],
            name="fk_catalog_relation_sources_relation_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["catalog_sources.id"],
            name="fk_catalog_relation_sources_source_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_catalog_relation_sources"),
        sa.UniqueConstraint("relation_id", "source_id", name="uq_catalog_relation_source"),
    )


def upgrade() -> None:
    create_districts()
    create_entities()
    create_entity_texts()
    create_entity_names()
    create_relations()
    create_sources()
    create_source_links()


def downgrade() -> None:
    op.drop_table("catalog_relation_sources")
    op.drop_table("catalog_entity_sources")
    op.drop_table("catalog_sources")
    op.drop_table("catalog_relations")
    op.drop_table("catalog_entity_names")
    op.drop_table("catalog_entity_texts")
    op.drop_table("catalog_entities")
    op.drop_table("catalog_districts")
