from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from common.base_model import BaseDBModel
from config import get_settings
from modules.audit import models as audit_models  # noqa: F401
from modules.auth import models as auth_models  # noqa: F401
from modules.catalog import models as catalog_models  # noqa: F401
from modules.media import models as media_models  # noqa: F401
from modules.moderation import models as moderation_models  # noqa: F401
from modules.publication import models as publication_models  # noqa: F401
from modules.submissions import models as submission_models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = BaseDBModel.metadata
APPLICATION_TABLE_PREFIXES = (
    "auth_",
    "catalog_",
    "media_",
    "audit_",
    "submissions_",
    "moderation_",
)
MIGRATION_OWNED_EXPRESSION_INDEXES = {
    "ix_catalog_entity_names_name_fts_ce",
    "ix_catalog_entity_names_name_fts_ru",
    "ix_catalog_entity_names_name_trgm",
    "ix_catalog_entity_texts_title_fts_ce",
    "ix_catalog_entity_texts_title_fts_ru",
    "ix_catalog_entity_texts_title_trgm",
}


def include_application_object(
    _: object,
    name: str | None,
    type_: str,
    __: bool,
    ___: object | None,
) -> bool:
    """Keep extension-owned PostGIS objects outside Alembic ownership."""
    if type_ == "index" and name in MIGRATION_OWNED_EXPRESSION_INDEXES:
        return False
    if type_ == "table":
        return name is not None and name.startswith(APPLICATION_TABLE_PREFIXES)
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=include_application_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_sync_migrations(connection: object) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        include_object=include_application_object,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(run_sync_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
