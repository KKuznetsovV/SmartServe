from __future__ import annotations

from smartserve_shared import mq


async def test_publish_with_no_connection_returns_false() -> None:
    assert await mq.publish(None, "order.updated", {"id": "1"}) is False


async def test_connect_unreachable_returns_none() -> None:
    conn = await mq.connect("amqp://invalid-host:5672/")
    assert conn is None


def test_death_count_sums_x_death() -> None:
    assert mq.death_count(None) == 0
    assert mq.death_count({}) == 0
    assert mq.death_count({"x-death": [{"count": 2}, {"count": 3}]}) == 5
    assert mq.death_count({"x-death": [{"count": mq.MAX_RETRIES}]}) == mq.MAX_RETRIES
