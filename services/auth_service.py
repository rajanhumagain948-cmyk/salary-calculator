"""Authentication utilities."""
from __future__ import annotations

import hashlib
import hmac
import secrets


def hash_password(password: str, salt: bytes | None = None) -> str:
    if not password:
        raise ValueError("パスワードを入力してください。")

    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        200_000,
    )
    return f"{salt.hex()}:{digest.hex()}"


def verify_password(password: str, stored_value: str) -> bool:
    try:
        salt_hex, expected_hex = stored_value.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(expected_hex)
    except (ValueError, TypeError):
        return False

    actual = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        200_000,
    )
    return hmac.compare_digest(actual, expected)