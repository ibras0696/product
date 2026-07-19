from common.exceptions import ApplicationError, ConflictError, NotFoundError


class ModerationNotFoundError(NotFoundError):
    pass


class ModerationConflictError(ConflictError):
    pass


class InvalidModerationTransitionError(ApplicationError):
    code = "invalid_transition"
    status_code = 409
