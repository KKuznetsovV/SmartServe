"""RabbitMQ event bus: publish/consume helpers over a single durable topic exchange.

Event names are dotted routing keys (e.g. `order.updated`, `payment.completed`,
`catalog.item_updated`). Payloads are JSON-serializable dicts; consumers must tolerate
unknown extra fields (forward-compatible schema). Delivery is at-least-once — handlers
should be idempotent.

Routers must not call `publish()` directly: they write the transactional outbox and a
relay publishes after commit. `publish()` returns whether the broker accepted the message
so the relay can leave a row unpublished on failure.

`consume_forever()` reconnects with backoff. Failed handler deliveries go to a retry
queue (TTL) via a dead-letter exchange, then to a parking queue after `MAX_RETRIES`.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import aio_pika
from aio_pika.abc import AbstractIncomingMessage, AbstractRobustConnection

from smartserve_shared.outbox import handle_idempotent

EXCHANGE_NAME = "smartserve.events"
RETRY_EXCHANGE = "smartserve.events.retry"
PARK_EXCHANGE = "smartserve.events.park"
MAX_RETRIES = 5
RETRY_TTL_MS = 2000

logger = logging.getLogger("smartserve.mq")

EventHandler = Callable[..., Awaitable[None]]


async def connect(url: str) -> AbstractRobustConnection | None:
    """Open a robust (auto-reconnecting) connection, or None if the broker is unreachable."""
    try:
        return await aio_pika.connect_robust(url)
    except Exception:  # noqa: BLE001 — broker may be down at boot
        logger.warning("mq.connect: could not reach RabbitMQ", exc_info=True)
        return None


async def maintain_connection(app: Any, url: str) -> None:
    """Keep `app.state.mq_connection` connected, retrying if boot or the broker fails."""
    app.state.mq_required = True
    while True:
        try:
            conn = getattr(app.state, "mq_connection", None)
            if conn is None or getattr(conn, "is_closed", True):
                app.state.mq_connection = await connect(url)
            await asyncio.sleep(2)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — reconnect loop must not die
            logger.warning("mq.maintain_connection: retry in 5s", exc_info=True)
            await asyncio.sleep(5)


async def publish(connection: AbstractRobustConnection | None, routing_key: str, payload: dict[str, Any]) -> bool:
    """Publish one event. Returns False (and never raises) if the broker is unreachable."""
    if connection is None:
        return False
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
        return True
    except Exception:  # noqa: BLE001 — relay treats False as unpublished
        logger.warning("mq.publish: failed to publish %s", routing_key, exc_info=True)
        return False


def death_count(headers: dict[str, Any] | None) -> int:
    """Sum RabbitMQ `x-death` counts (retry hops through the DLX)."""
    if not headers:
        return 0
    deaths = headers.get("x-death") or []
    total = 0
    for death in deaths:
        try:
            total += int(death.get("count") or 0)
        except (TypeError, ValueError, AttributeError):
            continue
    return total


async def _park(message: AbstractIncomingMessage, park_exchange: Any) -> None:
    parked = aio_pika.Message(
        body=message.body,
        content_type=message.content_type,
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        headers=dict(message.headers or {}),
    )
    await park_exchange.publish(parked, routing_key=message.routing_key or "")


async def consume_forever(
    url: str,
    queue_name: str,
    routing_keys: list[str],
    handler: EventHandler,
    *,
    session_factory: Callable[[], Any] | None = None,
    processed_model: type | None = None,
) -> None:
    """Bind `queue_name` to `routing_keys` and process messages until cancelled.

    Failed deliveries dead-letter onto a per-queue retry queue with TTL, then back to
    the original binding. After `MAX_RETRIES` they are published to the parking exchange.
    When `processed_model` is set, duplicate `eventId`s are acked without re-running the handler.
    """
    while True:
        try:
            connection = await aio_pika.connect_robust(url)
            async with connection:
                channel = await connection.channel()
                await channel.set_qos(prefetch_count=10)
                exchange = await channel.declare_exchange(EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True)
                retry_exchange = await channel.declare_exchange(
                    RETRY_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True
                )
                park_exchange = await channel.declare_exchange(
                    PARK_EXCHANGE, aio_pika.ExchangeType.FANOUT, durable=True
                )
                queue = await channel.declare_queue(
                    queue_name,
                    durable=True,
                    arguments={"x-dead-letter-exchange": RETRY_EXCHANGE},
                )
                for routing_key in routing_keys:
                    await queue.bind(exchange, routing_key=routing_key)
                retry_queue = await channel.declare_queue(
                    f"{queue_name}.retry",
                    durable=True,
                    arguments={
                        "x-message-ttl": RETRY_TTL_MS,
                        "x-dead-letter-exchange": EXCHANGE_NAME,
                    },
                )
                await retry_queue.bind(retry_exchange, routing_key="#")
                park_queue = await channel.declare_queue(f"{queue_name}.park", durable=True)
                await park_queue.bind(park_exchange)

                async with queue.iterator() as it:
                    async for message in it:
                        await _dispatch(
                            message,
                            handler,
                            park_exchange,
                            session_factory=session_factory,
                            processed_model=processed_model,
                        )
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — consumer reconnects
            logger.warning("mq.consume_forever: connection lost on %s, retrying in 5s", queue_name, exc_info=True)
            await asyncio.sleep(5)


async def _dispatch(
    message: AbstractIncomingMessage,
    handler: EventHandler,
    park_exchange: Any,
    *,
    session_factory: Callable[[], Any] | None,
    processed_model: type | None,
) -> None:
    try:
        payload = json.loads(message.body)
    except json.JSONDecodeError:
        logger.warning("mq.consume: dropping unparsable message")
        await message.ack()
        return
    try:
        await handle_idempotent(
            session_factory, processed_model, handler, message.routing_key or "", payload
        )
        await message.ack()
    except Exception:  # noqa: BLE001 — nack/park instead of crashing the consumer
        logger.warning("mq.consume: handler failed on %s", message.routing_key, exc_info=True)
        if death_count(message.headers) >= MAX_RETRIES:
            try:
                await _park(message, park_exchange)
            except Exception:  # noqa: BLE001
                logger.warning("mq.consume: failed to park message", exc_info=True)
            await message.ack()
            return
        await message.reject(requeue=False)
