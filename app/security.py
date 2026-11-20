"""Password hashing using only the standard library (PBKDF2-HMAC-SHA256)."""
import hashlib
import hmac
import os

_PREFIX = "pbkdf2$"
_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"{_PREFIX}{_ITERATIONS}${salt.hex()}${digest.hex()}"


def is_hashed(stored: str) -> bool:
    return stored.startswith(_PREFIX)


def verify_password(password: str, stored: str) -> bool:
    """Verify against a hash. Legacy plain-text rows are still accepted
    (callers should re-hash them on successful login)."""
    if not is_hashed(stored):
        return hmac.compare_digest(password.encode(), stored.encode())
    try:
        _, iterations, salt_hex, digest_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except ValueError:
        return False
