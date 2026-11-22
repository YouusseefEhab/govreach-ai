from secrets import token_urlsafe

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError


_password_hasher = PasswordHasher(type=Type.ID, memory_cost=19456, time_cost=2, parallelism=1)


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


_dummy_hash = hash_password(token_urlsafe(32))


def verify_password(password: str, password_hash: str | None) -> bool:
    if password_hash is None or not password_hash.startswith("$argon2id$"):
        password_hash = None
    try:
        verified = _password_hasher.verify(password_hash or _dummy_hash, password)
    except (InvalidHashError, VerificationError, UnicodeError):
        return False
    return verified and password_hash is not None


def password_needs_rehash(password_hash: str) -> bool:
    return _password_hasher.check_needs_rehash(password_hash)
