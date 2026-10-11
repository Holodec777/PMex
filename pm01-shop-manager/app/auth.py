"""Хэширование паролей и правила доступа по ролям."""

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass

PBKDF2_ITERATIONS = 240_000


@dataclass(frozen=True)
class UserSession:
    user_id: int | None
    login: str
    full_name: str
    role: str
    role_title: str


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Пароль должен содержать не менее 8 символов")
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt_text, digest_text = stored_hash.split("$", maxsplit=3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, UnicodeError):
        return False


def guest_session() -> UserSession:
    return UserSession(None, "guest", "Гость", "guest", "Гость")


def can(user: UserSession, permission: str) -> bool:
    rules = {
        "catalog_filters": {"seller", "manager", "admin"},
        "orders": {"manager", "admin"},
        "product_write": {"admin"},
        "product_delete": {"admin"},
        "csv_import": {"admin"},
    }
    return user.role in rules.get(permission, set())
