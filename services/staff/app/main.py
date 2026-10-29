from contextlib import asynccontextmanager

from fastapi import FastAPI
from smartserve_shared import mq
from smartserve_shared.app_factory import create_service_app

from app.api.v1.router import api_router
from app.core.config import settings
from app.db import models  # noqa: F401 — ensure models are registered
from app.db.session import engine, get_db


@asynccontextmanager
async def lifespan_hooks(app: FastAPI):
    app.state.mq_connection = await mq.connect(settings.RABBITMQ_URL)
    yield
    if app.state.mq_connection is not None:
        await app.state.mq_connection.close()
    await engine.dispose()


def create_app() -> FastAPI:
    return create_service_app(
        "staff",
        settings,
        api_router,
        lifespan_hooks,
        get_db=get_db,
        title="SmartServe Staff Service",
    )


app = create_app()
