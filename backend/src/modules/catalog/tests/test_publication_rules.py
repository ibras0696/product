from uuid import uuid4

import pytest

from modules.catalog.domain import (
    CatalogEntity,
    CatalogRelation,
    EvidenceClassification,
    PublicationStatus,
    SelfRelationForbiddenError,
    Source,
    SourceRequiredError,
    SourceType,
)


def source(*, verified: bool, type_: SourceType = SourceType.BOOK) -> Source:
    return Source(id=uuid4(), type=type_, is_verified=verified)


def test_entity_can_publish_with_its_verified_source() -> None:
    entity = CatalogEntity(id=uuid4(), sources=(source(verified=True),))

    published = entity.publish()

    assert published.status is PublicationStatus.PUBLISHED
    assert entity.status is PublicationStatus.DRAFT


def test_relation_can_publish_with_its_verified_source() -> None:
    relation = CatalogRelation(
        id=uuid4(),
        source_entity_id=uuid4(),
        target_entity_id=uuid4(),
        sources=(source(verified=True),),
    )

    published = relation.publish()

    assert published.status is PublicationStatus.PUBLISHED


@pytest.mark.parametrize("evidence", [(), (source(verified=False),)])
def test_entity_publication_requires_its_verified_source(
    evidence: tuple[Source, ...],
) -> None:
    entity = CatalogEntity(id=uuid4(), sources=evidence)

    with pytest.raises(SourceRequiredError) as error:
        entity.publish()

    assert error.value.code == "source_required"


def test_relation_publication_requires_its_verified_source() -> None:
    relation = CatalogRelation(
        id=uuid4(),
        source_entity_id=uuid4(),
        target_entity_id=uuid4(),
        sources=(source(verified=False),),
    )

    with pytest.raises(SourceRequiredError):
        relation.publish()


def test_relation_cannot_link_entity_to_itself() -> None:
    entity_id = uuid4()

    with pytest.raises(SelfRelationForbiddenError) as error:
        CatalogRelation(id=uuid4(), source_entity_id=entity_id, target_entity_id=entity_id)

    assert error.value.code == "self_relation_forbidden"


def test_oral_testimony_remains_explicitly_attributed() -> None:
    testimony = source(verified=True, type_=SourceType.ORAL_TESTIMONY)

    assert testimony.evidence_classification is EvidenceClassification.ORAL_TESTIMONY
