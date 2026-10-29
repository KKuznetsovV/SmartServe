import asyncio
import contextlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from smartserve_shared import mq
from smartserve_shared.app_factory import create_service_app

from app.api.v1.router import api_router
from app.core.config import settings
from app.db import models  # noqa: F401 — ensure models are registered
from app.db.session import engine, get_db
from app.modules.ordering.events import handle_catalog_item_updated, handle_payment_completed


@asynccontextmanager
async def lifespan_hooks(app: FastAPI):
    app.state.mq_connection = await mq.connect(settings.RABBITMQ_URL)
    consumer_task = asyncio.create_task(
        mq.consume_forever(
            settings.RABBITMQ_URL, "ordering.payment_completed", ["payment.completed"], handle_payment_completed
        )
    )
    realtime_relay_task = asyncio.create_task(
        mq.consume_forever(
            settings.RABBITMQ_URL,
            "ordering.realtime_relay",
            ["catalog.item_updated"],
            handle_catalog_item_updated,
        )
    )
    yield
    consumer_task.cancel()
    realtime_relay_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await consumer_task
    with contextlib.suppress(asyncio.CancelledError):
        await realtime_relay_task
    if app.state.mq_connection is not None:
        await app.state.mq_connection.close()
    await engine.dispose()


def create_app() -> FastAPI:
    return create_service_app(
        "ordering",
        settings,
        api_router,
        lifespan_hooks,
        get_db=get_db,
        title="SmartServe Ordering Service",
    )


app = create_app()
