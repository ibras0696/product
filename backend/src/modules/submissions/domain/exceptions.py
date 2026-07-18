class SubmissionDomainError(ValueError):
    code: str


class InvalidTransitionError(SubmissionDomainError):
    code = "invalid_transition"


class VersionConflictError(SubmissionDomainError):
    code = "conflict"
