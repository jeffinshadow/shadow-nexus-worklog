import hashlib
import hmac
import secrets
import time

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from .config import config

_ph = PasswordHasher()


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(stored_hash: str, password: str) -> bool:
    try:
        _ph.verify(stored_hash, password)
        return True
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    try:
        return _ph.check_needs_rehash(stored_hash)
    except InvalidHashError:
        return True


def password_ok(password: str) -> bool:
    return (
        isinstance(password, str)
        and config.MIN_PASSWORD_LEN <= len(password) <= config.MAX_PASSWORD_LEN
    )


def new_token() -> str:
    return secrets.token_urlsafe(32)


# Alfabeto sem caracteres ambiguos (0/O/1/I/l) para uma senha temporaria que o
# admin repassa e o usuario digita. 12 chars * ~31 simbolos = ~59 bits: forte o
# suficiente para uma senha de uso unico (o usuario troca no proximo login).
_TEMP_PW_ALPHABET = "23456789abcdefghjkmnpqrstuvwxyz"


def generate_temp_password(length: int = 12) -> str:
    return "".join(secrets.choice(_TEMP_PW_ALPHABET) for _ in range(length))


def token_hash(token: str) -> str:
    # HMAC-SHA256 com SECRET_KEY como pepper (o token vive em claro no cookie).
    return hmac.new(
        config.SECRET_KEY.encode(), token.encode(), hashlib.sha256
    ).hexdigest()


class RateLimiter:
    """Janela fixa em memoria. Backend roda em um unico worker."""

    def __init__(self, max_hits: int, window_seconds: int):
        self.max = max_hits
        self.window = window_seconds
        self._hits: dict[str, tuple[float, int]] = {}

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        start, count = self._hits.get(key, (now, 0))
        if now - start >= self.window:
            start, count = now, 0
        count += 1
        self._hits[key] = (start, count)
        return count <= self.max


# Ate 10 tentativas de login por chave (IP e email) a cada 5 minutos.
login_limiter = RateLimiter(max_hits=10, window_seconds=300)
