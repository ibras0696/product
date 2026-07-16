import hashlib
import secrets


class SessionTokenManager:
    @staticmethod
    def create() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def digest(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
