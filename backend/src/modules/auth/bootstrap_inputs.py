from collections.abc import Mapping
from pathlib import Path

_MAX_SECRET_BYTES = 1024


def required_environment(environment: Mapping[str, str], name: str) -> str:
    value = environment.get(name)
    if value is None or not value.strip():
        raise ValueError(f"{name} is required")
    return value


def read_password(path_value: str) -> str:
    path = Path(path_value)
    if not path.is_file():
        raise ValueError("Admin bootstrap password file is missing")
    with path.open("rb") as secret_file:
        raw = secret_file.read(_MAX_SECRET_BYTES + 1)
    if len(raw) > _MAX_SECRET_BYTES:
        raise ValueError("Admin bootstrap password file is too large")
    try:
        password = raw.decode("utf-8").removesuffix("\n").removesuffix("\r")
    except UnicodeDecodeError as exc:
        raise ValueError("Admin bootstrap password file must be UTF-8") from exc
    if not password:
        raise ValueError("Admin bootstrap password file is empty")
    return password
