import json
from collections.abc import Mapping
from pathlib import Path
from types import TracebackType
from typing import Self, cast
from uuid import UUID

import pytest

from common.base_model import BaseDBModel
from modules.catalog.models import Entity
from modules.catalog.seed import (
    CatalogSeedService,
    SeedPayload,
    SeedValidationError,
    load_seed_batches,
)

SOURCE_ID = "00000000-0000-0000-0000-000000000101"
ENTITY_A_ID = "00000000-0000-0000-0000-000000000201"
ENTITY_B_ID = "00000000-0000-0000-0000-000000000202"
RELATION_ID = "00000000-0000-0000-0000-000000000301"
ENTITY_LINK_ID = "00000000-0000-0000-0000-000000000401"
RELATION_LINK_ID = "00000000-0000-0000-0000-000000000402"


class FakeSeedRepository:
    def __init__(self) -> None:
        self.records: dict[tuple[type[BaseDBModel], UUID], BaseDBModel] = {}
        self.staged: dict[tuple[type[BaseDBModel], UUID], BaseDBModel] = {}
        self.bulk_calls = 0

    async def existing(
        self, model: type[BaseDBModel], record_ids: set[UUID]
    ) -> Mapping[UUID, BaseDBModel]:
        self.bulk_calls += 1
        available = self.records | self.staged
        return {
            record_id: available[(model, record_id)]
            for record_id in record_ids
            if (model, record_id) in available
        }

    def add(self, instance: BaseDBModel) -> None:
        self.staged[(type(instance), instance.id)] = instance

    def finish(self, *, commit: bool) -> None:
        if commit:
            self.records.update(self.staged)
        self.staged.clear()


class FakeSeedUnitOfWork:
    def __init__(self, repository: FakeSeedRepository, outcomes: list[bool]) -> None:
        self.repository = repository
        self._outcomes = outcomes

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.repository.finish(commit=exc_type is None)
        self._outcomes.append(exc_type is None)


def source() -> dict[str, object]:
    return {
        "id": SOURCE_ID,
        "title": "Reviewed source",
        "type": "book",
        "description": "Bibliographic description",
        "is_verified": True,
        "status": "published",
    }


def entity(entity_id: str, slug: str) -> dict[str, object]:
    return {
        "id": entity_id,
        "type": "landmark",
        "slug": slug,
        "status": "published",
    }


def relation(target_id: str = ENTITY_B_ID) -> dict[str, object]:
    return {
        "id": RELATION_ID,
        "source_entity_id": ENTITY_A_ID,
        "target_entity_id": target_id,
        "type": "connected_with",
        "title_ru": "Связь",
        "description_ru": "Проверенное описание связи",
        "status": "published",
    }


def payload(*, include_links: bool = True, target_id: str = ENTITY_B_ID) -> SeedPayload:
    groups: dict[str, tuple[dict[str, object], ...]] = {
        "districts": (),
        "sources": (source(),),
        "entities": (entity(ENTITY_A_ID, "entity-a"), entity(ENTITY_B_ID, "entity-b")),
        "entity_texts": (),
        "entity_names": (),
        "relations": (relation(target_id),),
        "entity_sources": (),
        "relation_sources": (),
    }
    if include_links:
        groups["entity_sources"] = (
            {"id": ENTITY_LINK_ID, "entity_id": ENTITY_A_ID, "source_id": SOURCE_ID},
            {
                "id": "00000000-0000-0000-0000-000000000403",
                "entity_id": ENTITY_B_ID,
                "source_id": SOURCE_ID,
            },
        )
        groups["relation_sources"] = (
            {"id": RELATION_LINK_ID, "relation_id": RELATION_ID, "source_id": SOURCE_ID},
        )
    return SeedPayload(groups)


@pytest.mark.asyncio
async def test_seed_is_idempotent_with_stable_ids_and_counts() -> None:
    repository = FakeSeedRepository()
    outcomes: list[bool] = []
    service = CatalogSeedService(lambda: FakeSeedUnitOfWork(repository, outcomes))

    first = await service.seed(payload())
    repeated = await service.seed(payload())

    assert (first.created, first.unchanged) == (7, 0)
    assert (repeated.created, repeated.unchanged) == (0, 7)
    assert len(repository.records) == 7
    assert repository.bulk_calls == 16
    assert outcomes == [True, True]


@pytest.mark.asyncio
async def test_seed_can_preserve_existing_content_during_additive_import() -> None:
    repository = FakeSeedRepository()
    service = CatalogSeedService(lambda: FakeSeedUnitOfWork(repository, []))
    await service.seed(payload())
    changed = payload()
    cast(dict[str, object], changed.groups["entities"][0])["slug"] = "renamed"

    result = await service.seed(changed, preserve_existing=True)

    stored = cast(Entity, repository.records[(Entity, UUID(ENTITY_A_ID))])
    assert stored.slug == "entity-a"
    assert (result.created, result.unchanged, result.preserved) == (0, 6, 1)


@pytest.mark.asyncio
async def test_seed_treats_postgis_ewkb_as_the_same_coordinate() -> None:
    repository = FakeSeedRepository()
    service = CatalogSeedService(lambda: FakeSeedUnitOfWork(repository, []))
    seeded = payload()
    cast(dict[str, object], seeded.groups["entities"][0]).update(
        {"longitude": 45.6949, "latitude": 43.3178}
    )

    await service.seed(seeded)
    stored = cast(Entity, repository.records[(Entity, UUID(ENTITY_A_ID))])
    stored.coordinate = "0101000020E6100000C5FEB27BF2D846409B559FABADA84540"

    repeated = await service.seed(seeded)

    assert (repeated.created, repeated.unchanged) == (0, 7)


@pytest.mark.asyncio
async def test_seed_rolls_back_when_published_content_has_no_verified_source() -> None:
    repository = FakeSeedRepository()
    outcomes: list[bool] = []
    service = CatalogSeedService(lambda: FakeSeedUnitOfWork(repository, outcomes))

    with pytest.raises(SeedValidationError, match="published entity"):
        await service.seed(payload(include_links=False))

    assert repository.records == {}
    assert repository.staged == {}
    assert outcomes == [False]


@pytest.mark.asyncio
async def test_seed_rejects_self_relation_in_same_transaction() -> None:
    repository = FakeSeedRepository()
    outcomes: list[bool] = []
    service = CatalogSeedService(lambda: FakeSeedUnitOfWork(repository, outcomes))

    with pytest.raises(SeedValidationError, match="itself"):
        await service.seed(payload(target_id=ENTITY_A_ID))

    assert repository.records == {}
    assert outcomes == [False]


@pytest.mark.asyncio
async def test_seed_rejects_unpublished_source_for_published_content() -> None:
    invalid = payload()
    cast(dict[str, object], invalid.groups["sources"][0])["status"] = "draft"
    service = CatalogSeedService(lambda: FakeSeedUnitOfWork(FakeSeedRepository(), []))

    with pytest.raises(SeedValidationError, match="verified and published"):
        await service.seed(invalid)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("longitude", "latitude", "message"),
    [
        (1.0, None, "provided together"),
        (181.0, 40.0, "longitude"),
        (40.0, -91.0, "latitude"),
        (float("nan"), 40.0, "finite"),
    ],
)
async def test_seed_rejects_invalid_coordinate_pairs_and_ranges(
    longitude: float, latitude: float | None, message: str
) -> None:
    invalid = payload()
    cast(dict[str, object], invalid.groups["entities"][0]).update(
        {"longitude": longitude, "latitude": latitude}
    )
    service = CatalogSeedService(lambda: FakeSeedUnitOfWork(FakeSeedRepository(), []))

    with pytest.raises(SeedValidationError, match=message):
        await service.seed(invalid)


@pytest.mark.asyncio
async def test_seed_rejects_reversed_entity_period_before_database_flush() -> None:
    invalid = payload()
    cast(dict[str, object], invalid.groups["entities"][0]).update(
        {"period_from": 1900, "period_to": 1840}
    )
    service = CatalogSeedService(lambda: FakeSeedUnitOfWork(FakeSeedRepository(), []))

    with pytest.raises(SeedValidationError, match="period_from"):
        await service.seed(invalid)


@pytest.mark.asyncio
async def test_seed_rejects_blank_slug() -> None:
    invalid = payload()
    cast(dict[str, object], invalid.groups["entities"][0])["slug"] = "  "
    service = CatalogSeedService(lambda: FakeSeedUnitOfWork(FakeSeedRepository(), []))

    with pytest.raises(SeedValidationError, match="slug must not be blank"):
        await service.seed(invalid)


@pytest.mark.asyncio
async def test_seed_rejects_blank_text_and_rolls_back_late_failure() -> None:
    invalid = payload()
    cast(dict[str, object], invalid.groups["relations"][0])["title_ru"] = "  "
    repository = FakeSeedRepository()
    outcomes: list[bool] = []
    service = CatalogSeedService(lambda: FakeSeedUnitOfWork(repository, outcomes))

    with pytest.raises(SeedValidationError, match="title_ru must not be blank"):
        await service.seed(invalid)

    assert repository.records == {}
    assert repository.staged == {}
    assert outcomes == [False]


@pytest.mark.asyncio
async def test_seed_rejects_same_id_with_changed_content() -> None:
    repository = FakeSeedRepository()
    outcomes: list[bool] = []
    service = CatalogSeedService(lambda: FakeSeedUnitOfWork(repository, outcomes))
    await service.seed(payload())
    changed = payload()
    cast(dict[str, object], changed.groups["entities"][0])["slug"] = "renamed"

    with pytest.raises(SeedValidationError, match="conflicts with existing content"):
        await service.seed(changed)

    assert len(repository.records) == 7
    assert repository.staged == {}
    assert outcomes == [True, False]


def _write_batch(path: Path, seeded: SeedPayload) -> None:
    path.write_text(
        json.dumps({group: list(records) for group, records in seeded.groups.items()}),
        encoding="utf-8",
    )


@pytest.mark.asyncio
async def test_ordered_seed_directory_allows_exact_duplicates_and_is_idempotent(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "research_batches"
    directory.mkdir()
    first = payload()
    duplicate_source = SeedPayload(
        {group: (source(),) if group == "sources" else () for group in first.groups}
    )
    _write_batch(directory / "001-foundation.json", first)
    _write_batch(directory / "002-source-repeat.json", duplicate_source)

    batches = load_seed_batches(directory)
    repository = FakeSeedRepository()
    service = CatalogSeedService(lambda: FakeSeedUnitOfWork(repository, []))
    first_results = [await service.seed(batch) for batch in batches]
    repeated_results = [await service.seed(batch) for batch in batches]

    assert [(item.created, item.unchanged) for item in first_results] == [(7, 0), (0, 1)]
    assert [(item.created, item.unchanged) for item in repeated_results] == [(0, 7), (0, 1)]
    assert len(repository.records) == 7


def test_ordered_seed_directory_rejects_cross_batch_content_conflict(tmp_path: Path) -> None:
    directory = tmp_path / "research_batches"
    directory.mkdir()
    first = payload()
    changed_source = source()
    changed_source["title"] = "Conflicting source title"
    conflict = SeedPayload(
        {group: (changed_source,) if group == "sources" else () for group in first.groups}
    )
    _write_batch(directory / "001-foundation.json", first)
    _write_batch(directory / "002-conflict.json", conflict)

    with pytest.raises(SeedValidationError, match="conflicts across seed batches"):
        load_seed_batches(directory)
