"""Auth dependencies for the ai orchestrator — verifies the same JWTs `auth` issues but
never touches a database (ai owns no tables; see docs/microservices-plan.md §4). Role/
business_id claims embedded in the token at issuance time are trusted directly, same
convention as `services/_shared/security.py`'s TokenClaims.
"""

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from security import TokenClaims, TokenError, verify_token

bearer = HTTPBearer()


@dataclass
class AuthContext:
    claims: TokenClaims
    token: str  # raw JWT, forwarded to downstream services on every outbound call


async def get_auth_context(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> AuthContext:
    try:
        claims = verify_token(credentials.credentials)
    except TokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc
    return AuthContext(claims=claims, token=credentials.credentials)


def require_role(*roles: str):
    """Dependency factory: raises 403 if the token's role claim is not in the allowed set."""

    async def _check(ctx: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if ctx.claims.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{ctx.claims.role}' is not permitted for this action",
            )
        return ctx

    return _check


require_manager = require_role("owner", "manager")
