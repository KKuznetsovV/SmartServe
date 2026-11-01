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

Dead-lettering on the consumer queues is applied with a RabbitMQ policy, not queue
arguments, so a broker that still has pre-E5 queues (no DLX args) can start.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import unquote, urlparse

import aio_pika
import httpx
from aio_pika.abc import AbstractIncomingMessage, AbstractRobustConnection

from smartserve_shared.outbox import handle_idempotent

EXCHANGE_NAME = "smartserve.events"
RETRY_EXCHANGE = "smartserve.events.retry"
PARK_EXCHANGE = "smartserve.events.park"
MAX_RETRIES = 5
RETRY_TTL_MS = 2000
DLX_POLICY_NAME = "smartserve-consumer-dlx"
DLX_POLICY_PATTERN = (
    r"^(ordering\.(payment_completed|realtime)|printing\.order_item_fired|reporting\.audit_log)$"
)

logger = logging.getLogger("smartserve.mq")

EventHandler = Callable[..., Awaitable[None]]


class ConsumerHealth:
    """Tracks whether a `consume_forever` loop is bound, or stuck reconnecting."""

    def __init__(self) -> None:
        self.connected = False


def register_consumer(app: Any, health: ConsumerHealth) -> None:
    leases = getattr(app.state, "mq_consumers", None)
    if leases is None:
        app.state.mq_consumers = []
        leases = app.state.mq_consumers
    leases.append(health)


def consumers_unhealthy(app: Any) -> bool:
    leases = getattr(app.state, "mq_consumers", None)
    if not leases:
        return False
    return any(not item.connected for item in leases)


def spawn_consumer(
    app: Any,
    url: str,
    queue_name: str,
    routing_keys: list[str],
    handler: EventHandler,
    **kwargs: Any,
) -> asyncio.Task[None]:
    health = ConsumerHealth()
    register_consumer(app, health)
    return asyncio.create_task(
        consume_forever(url, queue_name, routing_keys, handler, health=health, **kwargs)
    )


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


def management_origin(amqp_url: str) -> tuple[str, str, str]:
    """HTTP origin + credentials for the RabbitMQ management plugin."""
    parsed = urlparse(amqp_url)
    host = parsed.hostname or "localhost"
    user = unquote(parsed.username or "guest")
    password = unquote(parsed.password or "guest")
    return f"http://{host}:15672", user, password


async def ensure_dlx_policy(amqp_url: str) -> None:
    """Attach dead-lettering via policy so queue arguments never have to change."""
    origin, user, password = management_origin(amqp_url)
    url = f"{origin}/api/policies/%2F/{DLX_POLICY_NAME}"
    body = {
        "pattern": DLX_POLICY_PATTERN,
        "apply-to": "queues",
        "definition": {"dead-letter-exchange": RETRY_EXCHANGE},
        "priority": 0,
    }
    async with httpx.AsyncClient(auth=(user, password), timeout=5.0) as client:
        resp = await client.put(url, json=body)
        resp.raise_for_status()


async def declare_compatible_queue(channel: Any, name: str, *, arguments: dict[str, Any] | None = None) -> Any:
    """Declare a durable queue, or reuse one whose arguments already differ (pre-E5)."""
    try:
        if arguments is None:
            return await channel.declare_queue(name, durable=True)
        return await channel.declare_queue(name, durable=True, arguments=arguments)
    except Exception:  # noqa: BLE001 — PRECONDITION_FAILED on argument mismatch
        logger.warning("mq.declare_queue: reusing existing %s", name, exc_info=True)
        return await channel.declare_queue(name, durable=True, passive=True)


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
    health: ConsumerHealth | None = None,
) -> None:
    """Bind `queue_name` to `routing_keys` and process messages until cancelled.

    Failed deliveries dead-letter onto a per-queue retry queue with TTL, then back to
    the original binding. After `MAX_RETRIES` they are published to the parking exchange.
    When `processed_model` is set, duplicate `eventId`s are acked without re-running the handler.
    """
    while True:
        if health is not None:
            health.connected = False
        try:
            await ensure_dlx_policy(url)
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
                queue = await declare_compatible_queue(channel, queue_name)
                for routing_key in routing_keys:
                    await queue.bind(exchange, routing_key=routing_key)
                retry_queue = await declare_compatible_queue(
                    channel,
                    f"{queue_name}.retry",
                    arguments={
                        "x-message-ttl": RETRY_TTL_MS,
                        "x-dead-letter-exchange": EXCHANGE_NAME,
                    },
                )
                await retry_queue.bind(retry_exchange, routing_key="#")
                park_queue = await declare_compatible_queue(channel, f"{queue_name}.park")
                await park_queue.bind(park_exchange)

                if health is not None:
                    health.connected = True
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
            if health is not None:
                health.connected = False
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
