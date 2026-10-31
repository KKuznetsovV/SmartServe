"""Claims-only JWT check plus a cached auth lookup so demotions take effect."""

from __future__ import annotations

import json
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from httpx import HTTPStatusError
from smartserve_shared.deps import AuthContext
from smartserve_shared.security import TokenError, verify_token

from app.clients import auth_client

bearer = HTTPBearer()

AUTH_CACHE_TTL = 60
AUTH_CACHE_PREFIX = "ai:auth:"


async def lookup_cached_user(request: Request, token: str, user_id: str) -> dict[str, Any]:
    redis = getattr(request.app.state, "redis", None)
    key = f"{AUTH_CACHE_PREFIX}{user_id}"
    if redis is not None:
        cached = await redis.get(key)
        if cached:
            if isinstance(cached, bytes):
                cached = cached.decode()
            return json.loads(cached)
    try:
        response = await auth_client.get("/api/v1/auth/me", forward_token=token)
    except HTTPStatusError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found") from exc
    profile = response.json()
    if redis is not None:
        await redis.set(key, json.dumps(profile), ex=AUTH_CACHE_TTL)
    return profile


async def get_auth_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> AuthContext:
    try:
        claims = verify_token(credentials.credentials)
    except TokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc
    profile = await lookup_cached_user(request, credentials.credentials, claims.sub)
    if profile.get("active") is False:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found")
    db_role = profile.get("role")
    if claims.role and db_role and db_role != claims.role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Role is no longer valid")
    return AuthContext(claims=claims, token=credentials.credentials)


def require_role(*roles: str):
    async def _check(ctx: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if ctx.claims.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{ctx.claims.role}' is not permitted for this action",
            )
        return ctx

    return _check


require_manager = require_role("owner", "manager")

__all__ = ["AuthContext", "get_auth_context", "require_manager", "require_role"]
