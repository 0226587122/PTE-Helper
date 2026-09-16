"""Password hashing, session tokens and the auth dependencies."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import User

_hasher = PasswordHasher()
_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_token(user: User) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    claims = {
        "sub": str(user.id),
        "role": user.role,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expire_hours),
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=_ALGORITHM)


def set_session_cookie(response: Response, user: User) -> None:
    settings = get_settings()
    response.set_cookie(
        settings.cookie_name,
        create_token(user),
        max_age=settings.jwt_expire_hours * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        settings.cookie_name, path="/", httponly=True, secure=settings.cookie_secure, samesite="lax"
    )


def _user_from_request(request: Request, db: Session) -> User | None:
    settings = get_settings()
    token = request.cookies.get(settings.cookie_name)
    if not token:
        return None
    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        return None
    return db.get(User, int(claims["sub"]))


def current_user(request: Request, db: Annotated[Session, Depends(get_db)]) -> User:
    user = _user_from_request(request, db)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please sign in to continue.")
    return user


def require_admin(user: Annotated[User, Depends(current_user)]) -> User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You need an admin account for this.")
    return user


DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]
AdminUser = Annotated[User, Depends(require_admin)]
