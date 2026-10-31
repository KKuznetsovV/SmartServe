"""FastAPI app factory shared by every backend service."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from inspect import isasyncgenfunction
from typing import Any

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from smartserve_shared.logging import setup_logging
from smartserve_shared.security import configure_security_from_settings

logger = structlog.get_logger()


def _limiter_storage_uri() -> str:
    uri = os.environ.get("REDIS_URL", "")
    if uri.startswith("redis://") or uri.startswith("rediss://"):
        return uri
    return "memory://"


limiter = Limiter(key_func=get_remote_address, storage_uri=_limiter_storage_uri())

LifespanHooks = Callable[
    [FastAPI], AsyncIterator[None] | AbstractAsyncContextManager[Any]
]


def create_service_app(
    name: str,
    settings: Any,
    api_router: Any,
    lifespan_hooks: LifespanHooks | None = None,
    *,
    get_db: Any | None = None,
    title: str | None = None,
) -> FastAPI:
    """Build a service app with CORS, security headers, health, slowapi, and X-Served-By."""
    if hasattr(settings, "SECRET_KEY"):
        configure_security_from_settings(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        setup_logging(getattr(settings, "ENVIRONMENT", "development"))
        if getattr(settings, "ENVIRONMENT", "development") == "production" and str(
            getattr(settings, "SECRET_KEY", "")
        ).startswith("change-me"):
            raise RuntimeError("SECRET_KEY must be changed in production!")
        logger.info(
            f"{name} service starting",
            env=getattr(settings, "ENVIRONMENT", "development"),
        )
        if lifespan_hooks is not None:
            hook_cm = (
                asynccontextmanager(lifespan_hooks)(app)
                if isasyncgenfunction(lifespan_hooks)
                else lifespan_hooks(app)
            )
            async with hook_cm:
                yield
        else:
            yield
        logger.info(f"{name} service shutdown")

    app = FastAPI(
        title=title or f"SmartServe {name.title()} Service",
        version="0.1.0",
        docs_url="/docs"
        if getattr(settings, "ENVIRONMENT", "development") != "production"
        else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    app.state.mq_connection = None
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(
        _request: Request, exc: IntegrityError
    ) -> JSONResponse:
        orig = getattr(exc, "orig", None)
        logger.warning("database_integrity_error", error=str(orig or exc))
        return JSONResponse(
            status_code=409,
            content={"detail": "The change conflicts with existing data"},
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=getattr(settings, "CORS_ORIGINS", []),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next: object) -> Response:
        response: Response = await call_next(request)  # type: ignore[operator]
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Served-By"] = name
        if getattr(settings, "ENVIRONMENT", "development") == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains"
            )
        return response

    async def _db_ping() -> None:
        provider = app.dependency_overrides.get(get_db, get_db)
        async for session in provider():
            await session.execute(text("SELECT 1"))
            break

    def _broker_missing() -> bool:
        if not getattr(app.state, "mq_required", False):
            return False
        conn = getattr(app.state, "mq_connection", None)
        return conn is None or getattr(conn, "is_closed", True)

    if get_db is not None:

        @app.get("/api/v1/health")
        async def health_db() -> dict[str, str]:
            await _db_ping()
            return {"status": "ok", "db": "ok", "service": f"smartserve-{name}"}

        @app.get("/api/v1/ready")
        async def ready_db() -> JSONResponse:
            missing: list[str] = []
            try:
                await _db_ping()
            except Exception:  # noqa: BLE001 — any DB failure means not ready
                missing.append("db")
            if _broker_missing():
                missing.append("broker")
            if missing:
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "not_ready",
                        "missing": missing,
                        "service": f"smartserve-{name}",
                    },
                )
            return JSONResponse(
                content={"status": "ok", "service": f"smartserve-{name}"}
            )

    else:

        @app.get("/api/v1/health")
        async def health() -> dict[str, str]:
            return {"status": "ok", "service": f"smartserve-{name}"}

        @app.get("/api/v1/ready")
        async def ready() -> JSONResponse:
            if _broker_missing():
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "not_ready",
                        "missing": ["broker"],
                        "service": f"smartserve-{name}",
                    },
                )
            return JSONResponse(
                content={"status": "ok", "service": f"smartserve-{name}"}
            )

    app.include_router(api_router, prefix="/api/v1")
    return app
