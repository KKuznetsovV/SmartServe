import asyncio
import contextlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from smartserve_shared import mq
from smartserve_shared.app_factory import create_service_app
from smartserve_shared.outbox import relay_forever

from app.api.v1.router import api_router
from app.core.config import settings
from app.db import models  # noqa: F401 — ensure models are registered
from app.db.models import Outbox
from app.db.session import AsyncSessionLocal, engine, get_db


@asynccontextmanager
async def lifespan_hooks(app: FastAPI):
    reconnect = asyncio.create_task(mq.maintain_connection(app, settings.RABBITMQ_URL))
    relay = asyncio.create_task(relay_forever(lambda: app.state.mq_connection, AsyncSessionLocal, Outbox))
    yield
    reconnect.cancel()
    relay.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await reconnect
    with contextlib.suppress(asyncio.CancelledError):
        await relay
    if app.state.mq_connection is not None:
        await app.state.mq_connection.close()
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
