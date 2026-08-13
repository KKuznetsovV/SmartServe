from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core import mq
from app.core.config import settings
from app.core.logging import setup_logging
from app.db import models  # noqa: F401 — ensure models are registered
from app.db.session import engine, get_db

logger = structlog.get_logger()

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    if settings.ENVIRONMENT == "production" and settings.SECRET_KEY.startswith("change-me"):
        raise RuntimeError("SECRET_KEY must be changed in production!")
    logger.info("catalog service starting", env=settings.ENVIRONMENT)
    app.state.mq_connection = await mq.connect(settings.RABBITMQ_URL)
    yield
    if app.state.mq_connection is not None:
        await app.state.mq_connection.close()
    await engine.dispose()
    logger.info("catalog service shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="SmartServe Catalog Service",
        version="0.1.0",
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    app.state.mq_connection = None
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
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
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response

    @app.get("/api/v1/health")
    async def health(db=None):  # noqa: ANN001 — kept simple, matches apps/api's health contract
        async for session in get_db():
            await session.execute(text("SELECT 1"))
            break
        return {"status": "ok", "db": "ok", "service": "smartserve-catalog"}

    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
