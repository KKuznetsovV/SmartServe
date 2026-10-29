from contextlib import asynccontextmanager

from fastapi import FastAPI
from smartserve_shared.app_factory import create_service_app

from app.api.v1.router import api_router
from app.core.config import settings
from app.db import models  # noqa: F401 — ensure models are registered
from app.db.session import engine, get_db


@asynccontextmanager
async def lifespan_hooks(_app: FastAPI):
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    return create_service_app(
        "auth",
        settings,
        api_router,
        lifespan_hooks,
        get_db=get_db,
        title="SmartServe Auth Service",
    )


app = create_app()
