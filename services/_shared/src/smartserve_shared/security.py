"""JWT and password helpers shared across backend services.

`auth` is the only service that issues tokens. Every other service verifies the same
JWTs locally with this module — there is no per-request round-trip to `auth`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
from fastapi import HTTPException, status

DEFAULT_SECRET_KEY = "change-me-in-production-use-a-256-bit-random-string"
ALGORITHM = "HS256"

_secret_key_override: str | None = None
_algorithm_override: str | None = None
_access_expire_minutes: int = 15
_refresh_expire_days: int = 7


def configure_security(
    *,
    secret_key: str,
    algorithm: str = ALGORITHM,
    access_expire_minutes: int = 15,
    refresh_expire_days: int = 7,
) -> None:
    """Bind token settings from a service's Settings object (called from the app factory)."""
    global _secret_key_override, _algorithm_override, _access_expire_minutes, _refresh_expire_days
    _secret_key_override = secret_key
    _algorithm_override = algorithm
    _access_expire_minutes = access_expire_minutes
    _refresh_expire_days = refresh_expire_days


def configure_security_from_settings(settings: Any) -> None:
    configure_security(
        secret_key=settings.SECRET_KEY,
        algorithm=getattr(settings, "ALGORITHM", ALGORITHM),
        access_expire_minutes=int(getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 15)),
        refresh_expire_days=int(getattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS", 7)),
    )


def _secret_key() -> str:
    if _secret_key_override is not None:
        return _secret_key_override
    return os.environ.get("SECRET_KEY", DEFAULT_SECRET_KEY)


def _algorithm() -> str:
    if _algorithm_override is not None:
        return _algorithm_override
    return os.environ.get("ALGORITHM", ALGORITHM)


@dataclass(frozen=True)
class TokenClaims:
    sub: str
    business_id: str | None
    location_id: str | None
    role: str | None


class TokenError(Exception):
    """Raised when a JWT is missing, expired, or fails signature/claim validation."""


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=_access_expire_minutes)
    payload = {"sub": subject, "exp": expire, "type": "access", **(extra or {})}
    return jwt.encode(payload, _secret_key(), algorithm=_algorithm())


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(UTC) + timedelta(days=_refresh_expire_days)
    payload = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, _secret_key(), algorithm=_algorithm())


def decode_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    try:
        payload = jwt.decode(token, _secret_key(), algorithms=[_algorithm()])
        if payload.get("type") != expected_type:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        return payload
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        ) from exc


def verify_token(token: str) -> TokenClaims:
    """Decode and validate a JWT, returning its claims.

    Raises TokenError on any expiry/signature/claim failure so callers can map it to a
    401 without depending on the `jwt` library's exception types directly.
    """
    try:
        payload = jwt.decode(token, _secret_key(), algorithms=[_algorithm()])
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc

    sub = payload.get("sub")
    if not sub:
        raise TokenError("token missing 'sub' claim")

    return TokenClaims(
        sub=sub,
        business_id=payload.get("business_id"),
        location_id=payload.get("location_id"),
        role=payload.get("role"),
    )
