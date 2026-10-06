"""Sign up, sign in, and who-am-I (SPEC §19, and the login flow)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import Settings, get_settings
from app.db import repositories as repo
from app.db.session import get_db
from app.errors import CredentialsError
from app.models import User
from app.services.auth import (
    create_token,
    hash_password,
    new_display_name_from_email,
    normalize_email,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

Db = Annotated[Session, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

MIN_PASSWORD_LENGTH = 8


class SignUpRequest(BaseModel):
    email: str = Field(max_length=255)
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=200)
    display_name: str | None = Field(default=None, max_length=80)


class LoginRequest(BaseModel):
    email: str = Field(max_length=255)
    password: str = Field(max_length=200)


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str


class AuthResponse(BaseModel):
    token: str
    user: UserOut


@router.post("/signup", response_model=AuthResponse, status_code=201)
def signup(body: SignUpRequest, db: Db, settings: SettingsDep) -> AuthResponse:
    email = normalize_email(body.email)
    display_name = (body.display_name or new_display_name_from_email(email))[:80]

    user = repo.create_user(
        db,
        user_id=str(uuid.uuid4()),
        email=email,
        password_hash=hash_password(body.password),
        display_name=display_name,
    )
    return AuthResponse(
        token=create_token(user.id, settings.secret_key),
        user=UserOut(id=user.id, email=user.email, display_name=user.display_name),
    )


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, db: Db, settings: SettingsDep) -> AuthResponse:
    user = repo.get_user_by_email(db, normalize_email(body.email))
    # Same message either way, so this cannot be used to enumerate accounts.
    if user is None or not verify_password(body.password, user.password_hash):
        raise CredentialsError("Email or password is incorrect.")
    return AuthResponse(
        token=create_token(user.id, settings.secret_key),
        user=UserOut(id=user.id, email=user.email, display_name=user.display_name),
    )


@router.get("/me", response_model=UserOut)
def me(user: Annotated[User, Depends(get_current_user)]) -> UserOut:
    return UserOut(id=user.id, email=user.email, display_name=user.display_name)
