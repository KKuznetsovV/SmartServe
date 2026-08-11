"""JWT verification shared across all backend services.

Every service verifies the same access token locally using this module — there is no
per-request round-trip to `auth` to check a token. `auth` is the only service that ever
*issues* tokens; every other service only *verifies* them.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import jwt

ALGORITHM = "HS256"


def _secret_key() -> str:
    secret = os.environ.get("SECRET_KEY")
    if not secret:
        raise RuntimeError("SECRET_KEY environment variable is required")
    return secret


@dataclass(frozen=True)
class TokenClaims:
    sub: str
    business_id: str | None
    location_id: str | None
    role: str | None


class TokenError(Exception):
    """Raised when a JWT is missing, expired, or fails signature/claim validation."""


def verify_token(token: str) -> TokenClaims:
    """Decode and validate a JWT, returning its claims.

    Raises TokenError on any expiry/signature/claim failure so callers can map it to a
    401 without depending on the `jwt` library's exception types directly.
    """
    try:
        payload = jwt.decode(token, _secret_key(), algorithms=[ALGORITHM])
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
