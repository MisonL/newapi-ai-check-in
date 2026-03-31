from __future__ import annotations

import binascii
import hashlib
import hmac
import os


PASSWORD_SCHEME = 'pbkdf2_sha256'
PASSWORD_ITERATIONS = 390000
PASSWORD_SALT_BYTES = 16


def hash_password(password: str) -> str:
    salt = os.urandom(PASSWORD_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, PASSWORD_ITERATIONS)
    return f'{PASSWORD_SCHEME}${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}'


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iterations_text, salt_hex, digest_hex = encoded.split('$', 3)
    except ValueError:
        return False
    if scheme != PASSWORD_SCHEME:
        return False
    try:
        iterations = int(iterations_text)
        salt = binascii.unhexlify(salt_hex)
        expected = binascii.unhexlify(digest_hex)
    except (ValueError, binascii.Error):
        return False
    actual = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return hmac.compare_digest(actual, expected)
