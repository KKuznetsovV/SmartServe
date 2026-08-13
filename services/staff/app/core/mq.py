"""RabbitMQ event bus: publish/consume helpers over a single durable topic exchange.

Event names are dotted routing keys (e.g. `order.updated`, `payment.completed`,
`catalog.item_updated`) — see docs/microservices-plan.md §4 for the full publisher/
subscriber table. Payloads are JSON-serializable dicts; consumers must tolerate unknown
extra fields (forward-compatible schema). Delivery is at-least-once — handlers should be
idempotent.

`publish()` is best-effort: if the broker is unreachable it logs and returns rather than
raising, so a RabbitMQ outage never breaks the primary request it was called from.
`consume_forever()` reconnects with backoff and is meant to run as a long-lived background
task started in a service's lifespan and cancelled on shutdown.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import aio_pika
from aio_pika.abc import AbstractRobustConnection

EXCHANGE_NAME = "smartserve.events"

logger = logging.getLogger("smartserve.mq")

EventHandler = Callable[[str, dict[str, Any]], Awaitable[None]]


async def connect(url: str) -> AbstractRobustConnection | None:
    """Open a robust (auto-reconnecting) connection, or None if the broker is unreachable."""
    try:
        return await aio_pika.connect_robust(url)
    except Exception:
        logger.warning("mq.connect: could not reach RabbitMQ, publishing disabled", exc_info=True)
        return None


async def publish(connection: AbstractRobustConnection | None, routing_key: str, payload: dict[str, Any]) -> None:
    """Best-effort publish: never raises, so a broker outage can't break the caller."""
    if connection is None:
        return
    try:
        channel = await connection.channel()
        exchange = await channel.declare_exchange(EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True)
        message = aio_pika.Message(
            body=json.dumps(payload).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await exchange.publish(message, routing_key=routing_key)
        await channel.close()
    except Exception:
        logger.warning("mq.publish: failed to publish %s", routing_key, exc_info=True)


async def consume_forever(
    url: str,
    queue_name: str,
    routing_keys: list[str],
    handler: EventHandler,
) -> None:
    """Bind `queue_name` to `routing_keys` on the shared exchange and process messages
    until cancelled, reconnecting with a fixed backoff if the broker is unreachable or the
    connection drops.
    """
    while True:
        try:
            connection = await aio_pika.connect_robust(url)
            async with connection:
                channel = await connection.channel()
                await channel.set_qos(prefetch_count=10)
                exchange = await channel.declare_exchange(EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True)
                queue = await channel.declare_queue(queue_name, durable=True)
                for routing_key in routing_keys:
                    await queue.bind(exchange, routing_key=routing_key)

                async with queue.iterator() as it:
                    async for message in it:
                        async with message.process(requeue=False):
                            try:
                                payload = json.loads(message.body)
                            except json.JSONDecodeError:
                                logger.warning("mq.consume: dropping unparsable message on %s", queue_name)
                                continue
                            await handler(message.routing_key or "", payload)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("mq.consume_forever: connection lost on %s, retrying in 5s", queue_name, exc_info=True)
            await asyncio.sleep(5)
