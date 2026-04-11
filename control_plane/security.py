from __future__ import annotations

import binascii
import hashlib
import hmac
import os

PASSWORD_SCHEME = 'pbkdf2_sha256'
PASSWORD_ITERATIONS = 120000
PASSWORD_SALT_BYTES = 16


def hash_password(password: str, iterations: int = PASSWORD_ITERATIONS) -> str:
    salt = os.urandom(PASSWORD_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return f'{PASSWORD_SCHEME}${iterations}${salt.hex()}${digest.hex()}'


def _parse_password_hash(encoded: str) -> tuple[int, bytes, bytes] | None:
    try:
        scheme, iterations_text, salt_hex, digest_hex = encoded.split('$', 3)
    except ValueError:
        return None
    if scheme != PASSWORD_SCHEME:
        return None
    try:
        iterations = int(iterations_text)
        salt = binascii.unhexlify(salt_hex)
        digest = binascii.unhexlify(digest_hex)
    except (ValueError, binascii.Error):
        return None
    return iterations, salt, digest


def verify_password(password: str, encoded: str) -> bool:
    parsed = _parse_password_hash(encoded)
    if parsed is None:
        return False
    iterations, salt, expected = parsed
    actual = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return hmac.compare_digest(actual, expected)


def password_needs_rehash(encoded: str, target_iterations: int) -> bool:
    parsed = _parse_password_hash(encoded)
    if parsed is None:
        return True
    iterations, _, _ = parsed
    return iterations != target_iterations
