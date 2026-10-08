import re
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from apps.api.auth import hash_password, issue_access_token, verify_password
from apps.api.database import get_session_factory
from packages.persistence.sqlalchemy import UserRecord

router = APIRouter(prefix="/auth", tags=["auth"])
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=200)


class LoginRequest(RegisterRequest):
    pass


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    user_id: str
    email: str


def _normalized_email(value: str) -> str:
    email = value.strip().lower()
    if not _EMAIL.match(email):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    return email


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest) -> AuthResponse:
    email = _normalized_email(request.email)
    session = get_session_factory()()
    try:
        existing = session.query(UserRecord).filter(UserRecord.email == email).first()
        if existing:
            raise HTTPException(status_code=409, detail="An account with that email already exists.")
        user = UserRecord(
            user_id=str(uuid4()),
            email=email,
            password_hash=hash_password(request.password),
            created_at=datetime.now(timezone.utc),
        )
        session.add(user)
        session.commit()
        token = issue_access_token(UUID(user.user_id), user.email)
        return AuthResponse(access_token=token, user_id=user.user_id, email=user.email)
    finally:
        session.close()


@router.post("/login", response_model=AuthResponse)
def login(request: LoginRequest) -> AuthResponse:
    email = _normalized_email(request.email)
    session = get_session_factory()()
    try:
        user = session.query(UserRecord).filter(UserRecord.email == email).first()
        if user is None or not verify_password(request.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password.")
        token = issue_access_token(__import__("uuid").UUID(user.user_id), user.email)
        return AuthResponse(access_token=token, user_id=user.user_id, email=user.email)
    finally:
        session.close()
