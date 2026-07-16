from common.exceptions import ConflictError, UnauthorizedError


class EmailAlreadyRegisteredError(ConflictError):
    code = "email_already_registered"


class InvalidCredentialsError(UnauthorizedError):
    code = "invalid_credentials"
