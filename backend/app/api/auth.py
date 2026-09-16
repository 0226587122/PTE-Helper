from datetime import datetime

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import User
from app.security import DB, CurrentUser, clear_session_cookie, hash_password, set_session_cookie, verify_password

router = APIRouter(prefix="/api", tags=["auth"])


class SignUpIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    display_name: str = Field(min_length=1, max_length=100)


class SignInIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=200)


class UserOut(BaseModel):
    id: int
    email: str
    display_name: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


@router.post("/auth/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def sign_up(body: SignUpIn, response: Response, db: DB) -> User:
    email = body.email.lower()
    if db.scalars(select(User).where(User.email == email)).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "There's already an account with that email. Try signing in.")
    user = User(email=email, password_hash=hash_password(body.password), display_name=body.display_name.strip())
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "There's already an account with that email. Try signing in.")
    db.refresh(user)
    set_session_cookie(response, user)
    return user


@router.post("/auth/signin", response_model=UserOut)
def sign_in(body: SignInIn, response: Response, db: DB) -> User:
    user = db.scalars(select(User).where(User.email == body.email.lower())).first()
    if user is None or not verify_password(user.password_hash, body.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "That email and password don't match. Please try again.")
    set_session_cookie(response, user)
    return user


@router.post("/auth/signout", status_code=status.HTTP_204_NO_CONTENT)
def sign_out(response: Response) -> Response:
    clear_session_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user
