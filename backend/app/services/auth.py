"""Accounts, password hashing, and bearer tokens.

SPEC §3 lists authentication as out of scope, but the data model is multi-user
and a shared laptop needs to tell two people apart. So this is deliberately the
smallest thing that works:

- passwords are hashed with PBKDF2-HMAC-SHA256 (stdlib, no native dependency)
- sessions are stateless HMAC-signed tokens, so no session table to expire
- `SECRET_KEY` signs tokens; rotating it logs everyone out
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass

from app.errors import AuthError, CredentialsError

TOKEN_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 days
PBKDF2_ROUNDS = 600_000
SALT_BYTES = 16


# ------------------------------------------------------------------ passwords


def hash_password(password: str) -> str:
    """Return `pbkdf2_sha256$rounds$salt$hash`, all base64url."""
    if not password:
        raise CredentialsError("Password must not be empty.")
    salt = os.urandom(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ROUNDS)
    return "$".join(
        [
            "pbkdf2_sha256",
            str(PBKDF2_ROUNDS),
            _b64(salt),
            _b64(digest),
        ]
    )


def verify_password(password: str, encoded: str) -> bool:
    """Constant-time verification. Never raises on a malformed stored hash."""
    try:
        algorithm, rounds, salt_b64, digest_b64 = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        salt = _unb64(salt_b64)
        expected = _unb64(digest_b64)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(rounds))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(candidate, expected)


# --------------------------------------------------------------------- tokens


@dataclass
class TokenPayload:
    user_id: str
    expires_at: int


def create_token(user_id: str, secret: str, *, ttl_seconds: int = TOKEN_TTL_SECONDS) -> str:
    expires_at = int(time.time()) + ttl_seconds
    body = f"{user_id}.{expires_at}"
    signature = _sign(body, secret)
    return f"{body}.{signature}"


def decode_token(token: str, secret: str) -> TokenPayload:
    parts = token.split(".")
    if len(parts) != 3:
        raise AuthError("Invalid session token.")
    user_id, expires_raw, signature = parts
    body = f"{user_id}.{expires_raw}"
    if not hmac.compare_digest(_sign(body, secret), signature):
        raise AuthError("Invalid session token.")
    try:
        expires_at = int(expires_raw)
    except ValueError as exc:
        raise AuthError("Invalid session token.") from exc
    if expires_at < int(time.time()):
        raise AuthError("Session expired. Please sign in again.")
    return TokenPayload(user_id=user_id, expires_at=expires_at)


def _sign(body: str, secret: str) -> str:
    digest = hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest()
    return _b64(digest)


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def normalize_email(email: str) -> str:
    cleaned = email.strip().lower()
    if "@" not in cleaned or cleaned.startswith("@") or cleaned.endswith("@"):
        raise AuthError("Enter a valid email address.")
    return cleaned


def new_display_name_from_email(email: str) -> str:
    return normalize_email(email).split("@")[0][:80] or "Explorer"


def random_suffix() -> str:
    return secrets.token_hex(4)
