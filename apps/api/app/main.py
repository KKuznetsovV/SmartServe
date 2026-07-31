from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.db import models  # noqa: F401 — ensure models are registered
from app.db.session import engine

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("SmartServe API starting", env=settings.ENVIRONMENT)
    yield
    await engine.dispose()
    logger.info("SmartServe API shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="SmartServe API",
        version="0.1.0",
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
