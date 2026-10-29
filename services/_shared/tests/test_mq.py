from __future__ import annotations

from smartserve_shared import mq


async def test_publish_with_no_connection_is_noop() -> None:
    await mq.publish(None, "order.updated", {"id": "1"})


async def test_connect_unreachable_returns_none() -> None:
    conn = await mq.connect("amqp://invalid-host:5672/")
    assert conn is None
