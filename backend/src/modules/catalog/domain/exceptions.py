class CatalogDomainError(ValueError):
    code: str


class SourceRequiredError(CatalogDomainError):
    code = "source_required"


class SelfRelationForbiddenError(CatalogDomainError):
    code = "self_relation_forbidden"
