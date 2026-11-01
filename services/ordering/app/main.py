import asyncio
import contextlib
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
import structlog
from fastapi import FastAPI
from smartserve_shared import mq
from smartserve_shared.app_factory import create_service_app
from smartserve_shared.outbox import relay_forever

from app.api.v1.router import api_router
from app.core.config import settings
from app.db import models  # noqa: F401 — ensure models are registered
from app.db.models import Outbox, ProcessedEvent
from app.db.session import AsyncSessionLocal, engine, get_db
from app.modules.ordering.events import handle_payment_event, handle_realtime
from app.modules.ordering.ws_router import bind_redis, subscribe_ws_forever

logger = structlog.get_logger()


async def _redis_fanout(app: FastAPI) -> None:
    while True:
        client = None
        try:
            client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            await client.ping()
            app.state.redis = client
            bind_redis(client)
            await subscribe_ws_forever()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — reconnect Redis like the broker
            logger.warning("ordering.redis: connection lost, retrying", exc_info=True)
            await asyncio.sleep(2)
        finally:
            bind_redis(None)
            app.state.redis = None
            if client is not None:
                with contextlib.suppress(Exception):
                    await client.aclose()


@asynccontextmanager
async def lifespan_hooks(app: FastAPI):
    app.state.redis = None
    reconnect = asyncio.create_task(mq.maintain_connection(app, settings.RABBITMQ_URL))
    relay = asyncio.create_task(relay_forever(lambda: app.state.mq_connection, AsyncSessionLocal, Outbox))
    consumer_task = mq.spawn_consumer(
        app,
        settings.RABBITMQ_URL,
        "ordering.payment_completed",
        ["payment.completed", "payment.refunded"],
        handle_payment_event,
        session_factory=AsyncSessionLocal,
        processed_model=ProcessedEvent,
    )
    realtime_task = mq.spawn_consumer(
        app,
        settings.RABBITMQ_URL,
        "ordering.realtime",
        ["order.*", "catalog.item_updated"],
        handle_realtime,
        session_factory=AsyncSessionLocal,
        processed_model=ProcessedEvent,
    )
    redis_task = asyncio.create_task(_redis_fanout(app))
    yield
    for task in (reconnect, relay, consumer_task, realtime_task, redis_task):
        task.cancel()
    for task in (reconnect, relay, consumer_task, realtime_task, redis_task):
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
