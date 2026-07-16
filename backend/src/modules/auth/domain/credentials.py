import unicodedata


class PasswordPolicyViolation(ValueError):
    pass


def normalize_email(email: str) -> str:
    return unicodedata.normalize("NFKC", email).strip().casefold()


def validate_password(password: str) -> None:
    length = len(password)
    if length < 12 or length > 128:
        raise PasswordPolicyViolation("Password must contain between 12 and 128 characters")
