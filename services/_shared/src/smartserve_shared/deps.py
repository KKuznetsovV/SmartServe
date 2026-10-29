"""Auth FastAPI dependencies: DB-backed user lookup, or claims-only for services with no DB."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from smartserve_shared.db import make_db_session
from smartserve_shared.security import TokenClaims, TokenError, decode_token, verify_token

bearer = HTTPBearer()


def make_auth_dependencies(user_model: type[Any], get_db: Callable[..., Any]) -> tuple[Any, Any, Any, Any, Any]:
    """Return get_current_user, require_role, require_manager, require_owner, require_staff.

    `user_model` must have `id`, `active`, and `role` attributes (SQLAlchemy mapped).
    """

    DbSession = make_db_session(get_db)

    async def get_current_user(
        db: DbSession,
        credentials: HTTPAuthorizationCredentials = Depends(bearer),
    ) -> Any:
        payload = decode_token(credentials.credentials)
        result = await db.execute(select(user_model).where(user_model.id == payload["sub"], user_model.active))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user

    def require_role(*roles: str):
        async def _check(user: Any = Depends(get_current_user)) -> Any:
            if user.role not in roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{user.role}' is not permitted for this action",
                )
            return user

        return _check

    require_manager = require_role("owner", "manager")
    require_owner = require_role("owner")
    require_staff = require_role("owner", "manager", "cashier", "waiter", "kitchen")
    return get_current_user, require_role, require_manager, require_owner, require_staff


@dataclass
class AuthContext:
    claims: TokenClaims
    token: str  # raw JWT, forwarded to downstream services on every outbound call


def make_claims_auth_dependencies() -> tuple[Any, Any, Any]:
    """Claims-only guards for services that have no user table (the ai orchestrator)."""

    async def get_auth_context(
        credentials: HTTPAuthorizationCredentials = Depends(bearer),
    ) -> AuthContext:
        try:
            claims = verify_token(credentials.credentials)
        except TokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
            ) from exc
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
    return get_auth_context, require_role, require_manager
