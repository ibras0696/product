from cryptography.fernet import Fernet

from config import get_settings


class SecretCipher:
    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode())

    @classmethod
    def from_settings(cls) -> "SecretCipher":
        key = get_settings().encryption_key
        if not key:
            raise RuntimeError("ENCRYPTION_KEY must be configured before storing secrets")
        return cls(key)

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str:
        return self._fernet.decrypt(value.encode()).decode()
