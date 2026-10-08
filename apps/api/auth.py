"""User authentication for the public AutoWorker application.

The public API uses short-lived signed bearer tokens. Passwords are stored as
PBKDF2 hashes; the legacy operator token remains supported for internal/demo
automation until the production migration is complete.
"""
import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from uuid import UUID

from fastapi import Header, HTTPException, status

from apps.api.database import get_settings
from packages.observability.metrics import AUTH_FAILURES


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    email: str
    role: str = "user"


def _secret() -> bytes:
    settings = get_settings()
    value = settings.auth_secret or (settings.api_token if settings.environment != "production" else None)
    if not value:
        raise RuntimeError("AUTOWORKER_AUTH_SECRET is required in production.")
    return value.encode()


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 240_000)
    return "pbkdf2_sha256$240000$" + base64.urlsafe_b64encode(salt).decode() + "$" + base64.urlsafe_b64encode(digest).decode()


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iterations, salt_b64, digest_b64 = encoded.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(digest_b64.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def issue_access_token(user_id: UUID, email: str, *, ttl_seconds: int = 3600) -> str:
    header = {"alg": "HS256", "typ": "AWJWT"}
    payload = {"sub": str(user_id), "email": email, "exp": int(time.time()) + ttl_seconds}
    def enc(value: object) -> str:
        return base64.urlsafe_b64encode(json.dumps(value, separators=(",", ":")).encode()).decode().rstrip("=")
    body = enc(header) + "." + enc(payload)
    signature = hmac.new(_secret(), body.encode(), hashlib.sha256).digest()
    return body + "." + base64.urlsafe_b64encode(signature).decode().rstrip("=")


def principal_from_token(token: str) -> Principal | None:
    try:
        body, signature = token.rsplit(".", 1)
        supplied = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
        expected = hmac.new(_secret(), body.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(supplied, expected):
            return None
        _, payload_b64 = body.split(".", 1)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "=" * (-len(payload_b64) % 4)))
        if int(payload["exp"]) < int(time.time()):
            return None
        return Principal(user_id=UUID(payload["sub"]), email=str(payload["email"]))
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def require_api_auth(authorization: str | None = Header(default=None)) -> Principal:
    """Accept a public user token; retain the legacy operator token for automation."""
    settings = get_settings()
    if not authorization or not authorization.startswith("Bearer "):
        if get_settings().environment != "production":
            return Principal(user_id=UUID(int=0), email="development@autoworker.local", role="operator")
        AUTH_FAILURES.labels("missing_bearer").inc()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required.", headers={"WWW-Authenticate": "Bearer"})

    supplied = authorization[7:].strip()
    principal = principal_from_token(supplied)
    if principal:
        return principal

    if settings.api_token and secrets.compare_digest(supplied, settings.api_token):
        return Principal(user_id=UUID(int=0), email="operator@autoworker.local", role="operator")

    AUTH_FAILURES.labels("invalid_token").inc()
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token.", headers={"WWW-Authenticate": "Bearer"})
