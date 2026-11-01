import asyncio
import contextlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from smartserve_shared import mq
from smartserve_shared.app_factory import create_service_app

from app.api.v1.router import api_router
from app.core.config import settings
from app.db import models  # noqa: F401 — ensure models are registered
from app.db.models import ProcessedEvent
from app.db.session import AsyncSessionLocal, engine, get_db
from app.modules.printing.events import handle_order_item_fired


@asynccontextmanager
async def lifespan_hooks(app: FastAPI):
    reconnect = asyncio.create_task(mq.maintain_connection(app, settings.RABBITMQ_URL))
    consumer_task = mq.spawn_consumer(
        app,
        settings.RABBITMQ_URL,
        "printing.order_item_fired",
        ["order.item_fired"],
        handle_order_item_fired,
        session_factory=AsyncSessionLocal,
        processed_model=ProcessedEvent,
    )
    yield
    reconnect.cancel()
    consumer_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await reconnect
    with contextlib.suppress(asyncio.CancelledError):
        await consumer_task
    if app.state.mq_connection is not None:
        await app.state.mq_connection.close()
    await engine.dispose()


def create_app() -> FastAPI:
    return create_service_app(
        "printing",
        settings,
        api_router,
        lifespan_hooks,
        get_db=get_db,
        title="SmartServe Printing Service",
    )


app = create_app()
