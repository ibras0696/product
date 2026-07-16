from typing import Final

from anyio import to_thread
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from argon2.low_level import Type

_DUMMY_PASSWORD: Final = "auth-timing-placeholder"


class Argon2idPasswordManager:
    def __init__(self) -> None:
        self._hasher = PasswordHasher(type=Type.ID)
        self._dummy_hash = self._hasher.hash(_DUMMY_PASSWORD)

    async def hash(self, password: str) -> str:
        return await to_thread.run_sync(self._hasher.hash, password)

    async def verify(self, password: str, password_hash: str | None) -> bool:
        candidate_hash = password_hash or self._dummy_hash
        try:
            return await to_thread.run_sync(self._hasher.verify, candidate_hash, password)
        except (InvalidHashError, VerifyMismatchError):
            return False
