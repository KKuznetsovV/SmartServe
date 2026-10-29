from __future__ import annotations

from types import SimpleNamespace

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from smartserve_shared.deps import make_auth_dependencies, make_claims_auth_dependencies
from smartserve_shared.security import configure_security, create_access_token


def test_claims_auth_does_not_use_db() -> None:
    configure_security(secret_key="test-secret-key-for-shared-package")
    get_auth_context, _require_role, require_manager = make_claims_auth_dependencies()
    app = FastAPI()

    @app.get("/me")
    async def who(ctx=Depends(get_auth_context)):  # noqa: ANN001
        return {"sub": ctx.claims.sub, "role": ctx.claims.role}

    @app.get("/mgr")
    async def mgr(ctx=Depends(require_manager)):  # noqa: ANN001
        return {"ok": True}

    token = create_access_token("u1", {"role": "waiter", "business_id": "b1"})
    owner = create_access_token("u2", {"role": "owner", "business_id": "b1"})
    client = TestClient(app)
    assert client.get("/me").status_code in {401, 403}
    assert client.get("/me", headers={"Authorization": f"Bearer {token}"}).json()["role"] == "waiter"
    assert client.get("/mgr", headers={"Authorization": f"Bearer {token}"}).status_code == 403
    assert client.get("/mgr", headers={"Authorization": f"Bearer {owner}"}).status_code == 200


def test_make_auth_dependencies_returns_named_guards() -> None:
    get_current_user, require_role, require_manager, require_owner, require_staff = make_auth_dependencies(
        SimpleNamespace, lambda: None
    )
    assert callable(get_current_user)
    assert callable(require_role)
    assert callable(require_manager)
    assert callable(require_owner)
    assert callable(require_staff)
