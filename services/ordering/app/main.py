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
from app.db.models import Outbox, ProcessedEvent
from app.db.session import AsyncSessionLocal, engine, get_db
from app.modules.ordering.events import handle_catalog_item_updated, handle_payment_completed


@asynccontextmanager
async def lifespan_hooks(app: FastAPI):
    reconnect = asyncio.create_task(mq.maintain_connection(app, settings.RABBITMQ_URL))
    relay = asyncio.create_task(relay_forever(lambda: app.state.mq_connection, AsyncSessionLocal, Outbox))
    consumer_task = asyncio.create_task(
        mq.consume_forever(
            settings.RABBITMQ_URL,
            "ordering.payment_completed",
            ["payment.completed"],
            handle_payment_completed,
            session_factory=AsyncSessionLocal,
            processed_model=ProcessedEvent,
        )
    )
    realtime_relay_task = asyncio.create_task(
        mq.consume_forever(
            settings.RABBITMQ_URL,
            "ordering.realtime_relay",
            ["catalog.item_updated"],
            handle_catalog_item_updated,
            session_factory=AsyncSessionLocal,
            processed_model=ProcessedEvent,
        )
    )
    yield
    for task in (reconnect, relay, consumer_task, realtime_relay_task):
        task.cancel()
    for task in (reconnect, relay, consumer_task, realtime_relay_task):
        with contextlib.suppress(asyncio.CancelledError):
            await task
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
