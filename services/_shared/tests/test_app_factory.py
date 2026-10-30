from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from smartserve_shared.app_factory import create_service_app
from smartserve_shared.routing import APIRouter


def test_create_service_app_health_and_served_by() -> None:
    settings = SimpleNamespace(
        ENVIRONMENT="development",
        SECRET_KEY="test-secret-key-for-shared-package",
        CORS_ORIGINS=["http://localhost:3000"],
        ALGORITHM="HS256",
        ACCESS_TOKEN_EXPIRE_MINUTES=15,
        REFRESH_TOKEN_EXPIRE_DAYS=7,
    )
    router = APIRouter()

    @router.get("/ping")
    async def ping() -> dict[str, str]:
        return {"pong": "ok"}

    app = create_service_app("auth", settings, router, title="SmartServe Auth Service")
    client = TestClient(app)
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "service": "smartserve-auth"}
    assert health.headers["X-Served-By"] == "auth"
    ping = client.get("/api/v1/ping")
    assert ping.json() == {"pong": "ok"}
    assert ping.headers["X-Content-Type-Options"] == "nosniff"
    ready = client.get("/api/v1/ready")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ok", "service": "smartserve-auth"}


def test_ready_503_when_broker_required_but_missing() -> None:
    settings = SimpleNamespace(
        ENVIRONMENT="development",
        SECRET_KEY="test-secret-key-for-shared-package",
        CORS_ORIGINS=[],
        ALGORITHM="HS256",
        ACCESS_TOKEN_EXPIRE_MINUTES=15,
        REFRESH_TOKEN_EXPIRE_DAYS=7,
    )
    app = create_service_app("ordering", settings, APIRouter())
    app.state.mq_required = True
    app.state.mq_connection = None
    client = TestClient(app)
    resp = client.get("/api/v1/ready")
    assert resp.status_code == 503
    assert resp.json()["missing"] == ["broker"]


def test_integrity_error_returns_409() -> None:
    settings = SimpleNamespace(
        ENVIRONMENT="development",
        SECRET_KEY="test-secret-key-for-shared-package",
        CORS_ORIGINS=[],
        ALGORITHM="HS256",
        ACCESS_TOKEN_EXPIRE_MINUTES=15,
        REFRESH_TOKEN_EXPIRE_DAYS=7,
    )
    router = APIRouter()

    @router.post("/conflict")
    async def conflict() -> dict[str, str]:
        raise IntegrityError("INSERT", {}, Exception("duplicate key"))

    app = create_service_app("catalog", settings, router)
    client = TestClient(app)
    resp = client.post("/api/v1/conflict")
    assert resp.status_code == 409
    assert resp.json() == {"detail": "The change conflicts with existing data"}


def test_json_logging_outside_development() -> None:
    import structlog

    from smartserve_shared.logging import setup_logging

    setup_logging("production")
    processors = structlog.get_config()["processors"]
    assert processors[-1].__class__.__name__ == "JSONRenderer"
    setup_logging("development")
    processors = structlog.get_config()["processors"]
    assert processors[-1].__class__.__name__ == "ConsoleRenderer"
