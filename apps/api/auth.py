"""API authentication boundary for operator and task-control endpoints."""

import secrets

from fastapi import Header, HTTPException, status

from apps.api.database import get_settings


def require_api_auth(authorization: str | None = Header(default=None)) -> str:
    """Require a bearer token in production; keep local development frictionless."""
    settings = get_settings()
    if settings.environment != "production":
        return "development"

    expected = settings.api_token
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication is not configured.",
        )

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    supplied = authorization[7:].strip()
    if not supplied or not secrets.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return "operator"
