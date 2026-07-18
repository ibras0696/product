from common.exceptions import ApplicationError, ConflictError, NotFoundError


class PublicationNotFoundError(NotFoundError):
    pass


class PublicationConflictError(ConflictError):
    pass


class InvalidPublicationTransitionError(ApplicationError):
    code = "invalid_transition"
    status_code = 409


class IdempotencyConflictError(ApplicationError):
    code = "idempotency_conflict"
    status_code = 409
