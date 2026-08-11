"""Redis pub/sub publish/subscribe helpers with a shared event-name/payload convention.

Event names are dotted strings, e.g. `order.updated`, `payment.completed`,
`catalog.item_updated` (see docs/microservices-plan.md §4 for the full table of
publishers/subscribers). Payloads are JSON-serializable dicts; consumers are
expected to be tolerant of unknown extra fields (forward-compatible schema).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import redis.asyncio as redis

CHANNEL_PREFIX = "smartserve"


def _channel(event_name: str) -> str:
    return f"{CHANNEL_PREFIX}.{event_name}"


async def publish(redis_client: redis.Redis, event_name: str, payload: dict[str, Any]) -> None:
    """Publish a JSON-encoded event to its channel."""
    await redis_client.publish(_channel(event_name), json.dumps(payload))


async def subscribe(redis_client: redis.Redis, *event_names: str) -> AsyncIterator[dict[str, Any]]:
    """Subscribe to one or more event names, yielding decoded JSON payloads as they arrive."""
    pubsub = redis_client.pubsub()
    channels = [_channel(name) for name in event_names]
    await pubsub.subscribe(*channels)
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            yield json.loads(message["data"])
    finally:
        await pubsub.unsubscribe(*channels)
        await pubsub.aclose()
