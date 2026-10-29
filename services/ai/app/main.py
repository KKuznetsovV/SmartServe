from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from smartserve_shared import mq
from smartserve_shared.app_factory import create_service_app

from app.api.v1.router import api_router
from app.core.config import settings
from app.modules.ai.services import local_classifier


@asynccontextmanager
async def lifespan_hooks(app: FastAPI):
    app.state.mq_connection = await mq.connect(settings.RABBITMQ_URL)
    app.state.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    if settings.LOCAL_MODEL_PATH:
        local_classifier.load_model(settings.LOCAL_MODEL_PATH)
    yield
    if app.state.mq_connection is not None:
        await app.state.mq_connection.close()
    await app.state.redis.aclose()


def create_app() -> FastAPI:
    return create_service_app(
        "ai",
        settings,
        api_router,
        lifespan_hooks,
        title="SmartServe AI Service",
    )


app = create_app()
