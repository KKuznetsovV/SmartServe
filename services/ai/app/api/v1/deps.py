"""Claims-only auth for the ai orchestrator — verifies JWTs without a database."""

from smartserve_shared.deps import AuthContext, make_claims_auth_dependencies

get_auth_context, require_role, require_manager = make_claims_auth_dependencies()

__all__ = ["AuthContext", "get_auth_context", "require_manager", "require_role"]
