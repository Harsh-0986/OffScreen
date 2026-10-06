"""Tests for signup, login, tokens, and protected routes."""

from __future__ import annotations

import time

import pytest

from app.errors import AuthError, CredentialsError
from app.services.auth import (
    create_token,
    decode_token,
    hash_password,
    normalize_email,
    verify_password,
)

CREDENTIALS = {"email": "walker@example.com", "password": "outdoors123"}


# ---------------------------------------------------------------- passwords


def test_password_hash_is_salted_and_verifiable() -> None:
    encoded = hash_password("outdoors123")
    assert verify_password("outdoors123", encoded)
    assert not verify_password("wrong", encoded)


def test_same_password_hashes_differently_each_time() -> None:
    assert hash_password("same") != hash_password("same")


def test_hash_never_contains_the_password() -> None:
    assert "outdoors123" not in hash_password("outdoors123")


def test_verify_rejects_a_malformed_stored_hash() -> None:
    assert not verify_password("x", "garbage")
    assert not verify_password("x", "pbkdf2_sha256$notanint$c2FsdA$aGFzaA")
    assert not verify_password("x", "")


def test_empty_password_is_refused() -> None:
    with pytest.raises(CredentialsError):
        hash_password("")


# ------------------------------------------------------------------- tokens


def test_token_round_trip() -> None:
    token = create_token("user-1", "secret")
    assert decode_token(token, "secret").user_id == "user-1"


def test_token_signed_with_another_secret_is_rejected() -> None:
    token = create_token("user-1", "secret")
    with pytest.raises(AuthError):
        decode_token(token, "different-secret")


def test_expired_token_is_rejected() -> None:
    token = create_token("user-1", "secret", ttl_seconds=-10)
    with pytest.raises(AuthError, match="expired"):
        decode_token(token, "secret")


def test_malformed_tokens_are_rejected() -> None:
    for bad in ["", "a.b", "a.b.c.d", "notatoken"]:
        with pytest.raises(AuthError):
            decode_token(bad, "secret")


def test_token_body_cannot_be_tampered_with() -> None:
    token = create_token("user-1", "secret")
    user_id, expires, signature = token.split(".")
    forged = f"{user_id}-evil.{expires}.{signature}"
    with pytest.raises(AuthError):
        decode_token(forged, "secret")


def test_token_expiry_is_in_the_future() -> None:
    payload = decode_token(create_token("u", "s"), "s")
    assert payload.expires_at > time.time()


# -------------------------------------------------------------------- email


def test_email_is_normalised() -> None:
    assert normalize_email("  Walker@Example.COM ") == "walker@example.com"


def test_invalid_emails_are_rejected() -> None:
    for bad in ["", "nope", "@example.com", "walker@"]:
        with pytest.raises(AuthError):
            normalize_email(bad)


# ----------------------------------------------------------------- endpoints


def test_signup_creates_an_account(client) -> None:
    response = client.post("/api/auth/signup", json={**CREDENTIALS, "display_name": "Walker"})
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "walker@example.com"
    assert body["user"]["display_name"] == "Walker"
    assert body["token"]


def test_signup_derives_a_display_name(client) -> None:
    body = client.post("/api/auth/signup", json=CREDENTIALS).json()
    assert body["user"]["display_name"] == "walker"


def test_duplicate_signup_is_refused(client) -> None:
    client.post("/api/auth/signup", json=CREDENTIALS)
    response = client.post("/api/auth/signup", json=CREDENTIALS)
    assert response.status_code == 409
    assert "already has an account" in response.json()["detail"]


def test_short_password_is_refused(client) -> None:
    response = client.post("/api/auth/signup", json={"email": "a@b.com", "password": "short"})
    assert response.status_code == 422


def test_login_succeeds(client) -> None:
    client.post("/api/auth/signup", json=CREDENTIALS)
    response = client.post("/api/auth/login", json=CREDENTIALS)
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "walker@example.com"


def test_login_is_case_insensitive_on_email(client) -> None:
    client.post("/api/auth/signup", json=CREDENTIALS)
    response = client.post(
        "/api/auth/login", json={"email": "WALKER@example.com", "password": "outdoors123"}
    )
    assert response.status_code == 200


def test_wrong_password_is_refused(client) -> None:
    client.post("/api/auth/signup", json=CREDENTIALS)
    response = client.post(
        "/api/auth/login", json={"email": "walker@example.com", "password": "nope12345"}
    )
    assert response.status_code == 401


def test_unknown_email_gives_the_same_message_as_a_wrong_password(client) -> None:
    """The login response must not reveal whether an email is registered."""
    client.post("/api/auth/signup", json=CREDENTIALS)
    unknown = client.post(
        "/api/auth/login", json={"email": "ghost@example.com", "password": "outdoors123"}
    ).json()["detail"]
    wrong = client.post(
        "/api/auth/login", json={"email": "walker@example.com", "password": "nope12345"}
    ).json()["detail"]
    assert unknown == wrong


def test_me_requires_a_token(client) -> None:
    assert client.get("/api/auth/me").status_code == 401


def test_me_returns_the_signed_in_user(client) -> None:
    token = client.post("/api/auth/signup", json=CREDENTIALS).json()["token"]
    body = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert body["email"] == "walker@example.com"


def test_me_rejects_a_token_for_a_deleted_account(client, db) -> None:
    token = client.post("/api/auth/signup", json=CREDENTIALS).json()["token"]
    from app.models import User

    user = db.query(User).one()
    db.delete(user)
    db.commit()
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
